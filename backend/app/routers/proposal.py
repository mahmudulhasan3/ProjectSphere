from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.services.notification_service import get_group_member_emails
from backend.app.core.email import send_proposal_decision_email
from backend.app.schemas.proposal import ProposalTopicInfo
from backend.app.db.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.group import Group, GroupMember
from backend.app.models.supervisor import Supervisor
from backend.app.models.proposal import Proposal, ProposalTopic
from backend.app.services.file_service import save_upload_file
from backend.app.services.semester_service import is_past_final_deadline
from backend.app.schemas.proposal import (
    ProposalDetail,
    ProposalRejectRequest,
    ProposalApproveRequest,
    AssignTopicRequest,
    MessageResponse,
)

router = APIRouter(prefix="/proposals", tags=["Proposal"])


def get_user_group(db: Session, user_id: int) -> GroupMember | None:
    return db.query(GroupMember).filter(GroupMember.student_id == user_id).first()


def get_supervisor_profile(db: Session, user_id: int) -> Supervisor | None:
    return db.query(Supervisor).filter(Supervisor.user_id == user_id).first()


def get_latest_proposal(db: Session, group_id: int) -> Proposal | None:
    return (
        db.query(Proposal)
        .filter(Proposal.group_id == group_id)
        .order_by(Proposal.round_number.desc())
        .first()
    )


def build_proposal_detail(
    db: Session, proposal: Proposal, duplicate_warning: str | None = None
) -> ProposalDetail:
    topics = (
        db.query(ProposalTopic).filter(ProposalTopic.proposal_id == proposal.id).all()
    )
    return ProposalDetail(
        id=proposal.id,
        group_id=proposal.group_id,
        round_number=proposal.round_number,
        status=proposal.status,
        feedback=proposal.feedback,
        resubmission_deadline=proposal.resubmission_deadline,
        suggested_area=proposal.suggested_area,
        topics=[ProposalTopicInfo.model_validate(t) for t in topics],
        duplicate_warning=duplicate_warning,
    )


def check_duplicate_titles(
    db: Session, titles: list[str], own_group_id: int
) -> str | None:
    all_topics = (
        db.query(ProposalTopic)
        .join(Proposal, ProposalTopic.proposal_id == Proposal.id)
        .filter(Proposal.group_id != own_group_id)
        .all()
    )
    for title in titles:
        for topic in all_topics:
            if title.strip().lower() == topic.title.strip().lower():
                return f"Similar title already exists: '{topic.title}'"
    return None


def can_group_self_submit(latest: Proposal | None) -> tuple[bool, str | None]:
    """Returns (allowed, reason_if_not)."""
    if latest is None:
        return True, None

    if latest.status != "rejected":
        return (
            True,
            None,
        )  # pending or approved - handled separately (active-pending check)

    if latest.round_number == 1:
        if latest.resubmission_deadline is None:
            return True, None  # safety fallback

        deadline = latest.resubmission_deadline.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) <= deadline:
            return True, None

        return (
            False,
            "Resubmission deadline has passed. Your supervisor will assign a topic directly.",
        )

    # round 2 or later, rejected - no more self-submission
    return (
        False,
        "Your proposal was rejected a second time. Your supervisor will assign a topic directly.",
    )


@router.post("/submit", response_model=ProposalDetail)
def submit_proposal(
    titles: list[str] = Form(...),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(titles) != len(files):
        raise HTTPException(
            status_code=400, detail="Number of titles must match number of files"
        )

    if not (1 <= len(titles) <= 3):
        raise HTTPException(
            status_code=400, detail="You must submit between 1 and 3 topics"
        )

    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    group = db.query(Group).filter(Group.id == membership.group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    if is_past_final_deadline(db, group):
        raise HTTPException(
            status_code=400, detail="Final submission deadline has passed"
        )

    if group.assigned_supervisor_id is None:
        raise HTTPException(
            status_code=400, detail="Your group doesn't have an assigned supervisor yet"
        )

    latest = get_latest_proposal(db, group.id)

    if latest is not None and latest.status == "pending":
        raise HTTPException(
            status_code=400, detail="You already have a proposal pending review"
        )

    allowed, reason = can_group_self_submit(latest)
    if not allowed:
        raise HTTPException(status_code=400, detail=reason)

    duplicate_warning = check_duplicate_titles(db, titles, group.id)

    next_round = (latest.round_number + 1) if latest else 1

    proposal = Proposal(group_id=group.id, round_number=next_round, status="pending")
    db.add(proposal)
    db.flush()

    try:
        for title, upload in zip(titles, files):
            saved_path = save_upload_file(upload, subfolder=f"proposals/{group.id}")
            db.add(
                ProposalTopic(proposal_id=proposal.id, title=title, file_url=saved_path)
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise

    db.refresh(proposal)

    return build_proposal_detail(db, proposal, duplicate_warning=duplicate_warning)


@router.get("/mine", response_model=ProposalDetail)
def get_my_latest_proposal(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    proposal = get_latest_proposal(db, membership.group_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="No proposal submitted yet")

    return build_proposal_detail(db, proposal)


@router.get("/pending-review", response_model=list[ProposalDetail])
def list_pending_reviews(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    supervisor = get_supervisor_profile(db, current_user.id)
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor profile not found")

    group_ids = [
        g.id
        for g in db.query(Group)
        .filter(Group.assigned_supervisor_id == supervisor.id)
        .all()
    ]

    proposals = (
        db.query(Proposal)
        .filter(Proposal.group_id.in_(group_ids), Proposal.status == "pending")
        .all()
    )

    results = []
    for proposal in proposals:
        titles = [
            t.title
            for t in db.query(ProposalTopic)
            .filter(ProposalTopic.proposal_id == proposal.id)
            .all()
        ]
        warning = check_duplicate_titles(db, titles, proposal.group_id)
        results.append(build_proposal_detail(db, proposal, duplicate_warning=warning))

    return results


def get_proposal_and_check_supervisor(
    db: Session, proposal_id: int, current_user: User
) -> Proposal:
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    supervisor = get_supervisor_profile(db, current_user.id)
    group = db.query(Group).filter(Group.id == proposal.group_id).first()
    if (
        group is None
        or supervisor is None
        or group.assigned_supervisor_id != supervisor.id
    ):
        raise HTTPException(
            status_code=403, detail="You are not the supervisor for this group"
        )

    return proposal


@router.post("/{proposal_id}/approve", response_model=MessageResponse)
def approve_proposal(
    proposal_id: int,
    payload: ProposalApproveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proposal = get_proposal_and_check_supervisor(db, proposal_id, current_user)

    if proposal.status != "pending":
        raise HTTPException(
            status_code=400, detail="This proposal has already been reviewed"
        )

    topic = (
        db.query(ProposalTopic)
        .filter(
            ProposalTopic.id == payload.approved_topic_id,
            ProposalTopic.proposal_id == proposal.id,
        )
        .first()
    )
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found in this proposal")

    proposal.status = "approved"
    proposal.approved_topic_id = topic.id
    db.commit()

    emails = get_group_member_emails(db, proposal.group_id)
    send_proposal_decision_email(emails, status="approved")

    return MessageResponse(message=f"Approved topic: {topic.title}")


@router.post("/{proposal_id}/reject", response_model=MessageResponse)
def reject_proposal(
    proposal_id: int,
    payload: ProposalRejectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proposal = get_proposal_and_check_supervisor(db, proposal_id, current_user)

    if proposal.status != "pending":
        raise HTTPException(
            status_code=400, detail="This proposal has already been reviewed"
        )

    if proposal.round_number >= 2:
        raise HTTPException(
            status_code=400,
            detail="This was already the second round. Use the assign-topic endpoint to assign a topic directly instead of rejecting again.",
        )

    proposal.status = "rejected"
    proposal.feedback = payload.feedback
    proposal.resubmission_deadline = payload.resubmission_deadline
    proposal.suggested_area = payload.suggested_area
    db.commit()

    emails = get_group_member_emails(db, proposal.group_id)
    send_proposal_decision_email(emails, status="rejected", feedback=payload.feedback)

    return MessageResponse(
        message=f"Rejected. Group must resubmit by {payload.resubmission_deadline}."
    )


@router.post("/{proposal_id}/assign-topic", response_model=MessageResponse)
def assign_topic_directly(
    proposal_id: int,
    payload: AssignTopicRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proposal = get_proposal_and_check_supervisor(db, proposal_id, current_user)

    if proposal.status == "approved":
        raise HTTPException(status_code=400, detail="This proposal is already approved")

    is_deadline_missed = (
        proposal.round_number == 1
        and proposal.status == "rejected"
        and proposal.resubmission_deadline is not None
        and datetime.now(timezone.utc)
        > proposal.resubmission_deadline.replace(tzinfo=timezone.utc)
    )
    is_second_reject = proposal.round_number >= 2 and proposal.status == "rejected"

    if not (is_deadline_missed or is_second_reject):
        raise HTTPException(
            status_code=400,
            detail="Direct topic assignment is only allowed after a second rejection or a missed resubmission deadline",
        )

    topic = ProposalTopic(
        proposal_id=proposal.id,
        title=payload.title,
        file_url=None,
        assigned_by_supervisor=True,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)

    proposal.status = "approved"
    proposal.approved_topic_id = topic.id
    db.commit()

    return MessageResponse(message=f"Topic assigned directly: {payload.title}")


@router.get("/history", response_model=list[ProposalDetail])
def get_proposal_history(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    proposals = (
        db.query(Proposal)
        .filter(Proposal.group_id == membership.group_id)
        .order_by(Proposal.round_number.asc())
        .all()
    )

    return [build_proposal_detail(db, p) for p in proposals]
