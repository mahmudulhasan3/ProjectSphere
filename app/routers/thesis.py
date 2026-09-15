from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import get_current_user, get_current_admin
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.supervisor import Supervisor
from app.models.thesis import Thesis
from app.services.file_service import save_upload_file
from app.services.semester_service import is_past_final_deadline
from app.core.email import send_email
from app.schemas.thesis import (
    ThesisInfo,
    ThesisReviewRequest,
    AdminThesisActionRequest,
    MessageResponse,
)
from app.models.student_profile import StudentProfile

router = APIRouter(tags=["Thesis"])


def get_user_group(db: Session, user_id: int) -> GroupMember | None:
    return db.query(GroupMember).filter(GroupMember.student_id == user_id).first()


def notify_admins(db: Session, subject: str, body: str) -> None:
    admins = db.query(User).filter(User.role == "admin").all()
    for admin in admins:
        send_email(admin.email, subject, body)


def determine_category(db: Session, group: Group) -> str:
    """A group is thesis-eligible only if its members are Level 4, Term 1 or 2.
    Since group join already enforces same level/term across members, checking
    the leader's profile is enough."""
    leader_profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == group.leader_id)
        .first()
    )
    if leader_profile is None:
        return "project"

    if leader_profile.level == "4" and leader_profile.term in ("1", "2"):
        return "thesis"

    return "project"


def is_thesis_eligible(db: Session, group: Group) -> bool:
    """Only Level 4, Term 1 or 2 groups are allowed to choose the 'thesis' category."""
    leader_profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == group.leader_id)
        .first()
    )
    if leader_profile is None:
        return False
    return leader_profile.level == "4" and leader_profile.term in ("1", "2")


@router.post("/theses/submit", response_model=ThesisInfo)
def submit_thesis(
    category: str = Form(...),  # "thesis" or "project" - chosen by the group
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if category not in ("thesis", "project"):
        raise HTTPException(
            status_code=400, detail="Category must be 'thesis' or 'project'"
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

    if category == "thesis" and not is_thesis_eligible(db, group):
        raise HTTPException(
            status_code=400,
            detail="Only Level 4, Term 1 or 2 groups can submit under the 'thesis' category",
        )

    active = (
        db.query(Thesis)
        .filter(
            Thesis.group_id == group.id,
            Thesis.status.in_(["pending", "revision_requested"]),
        )
        .first()
    )

    file_url = save_upload_file(file, subfolder=f"{category}s/{group.id}")

    if active is not None:
        active.manuscript_url = file_url
        active.status = "pending"
        active.category = category
        db.commit()
        db.refresh(active)
        thesis = active
    else:
        thesis = Thesis(
            group_id=group.id,
            category=category,
            manuscript_url=file_url,
            status="pending",
        )
        db.add(thesis)
        db.commit()
        db.refresh(thesis)

    notify_admins(
        db,
        f"ProjectSphere: {category.capitalize()} manuscript uploaded",
        f"<p>Group {group.id} ({group.name}) uploaded a {category} manuscript for review.</p>",
    )

    return thesis


@router.get("/theses/mine", response_model=ThesisInfo)
def get_my_thesis(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    thesis = (
        db.query(Thesis)
        .filter(Thesis.group_id == membership.group_id)
        .order_by(Thesis.id.desc())
        .first()
    )
    if thesis is None:
        raise HTTPException(status_code=404, detail="No thesis submitted yet")

    return thesis


@router.get("/theses/pending-review", response_model=list[ThesisInfo])
def list_pending_theses(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    supervisor = (
        db.query(Supervisor).filter(Supervisor.user_id == current_user.id).first()
    )
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor profile not found")

    group_ids = [
        g.id
        for g in db.query(Group)
        .filter(Group.assigned_supervisor_id == supervisor.id)
        .all()
    ]

    return (
        db.query(Thesis)
        .filter(Thesis.group_id.in_(group_ids), Thesis.status == "pending")
        .all()
    )


@router.post("/theses/{thesis_id}/review", response_model=MessageResponse)
def review_thesis(
    thesis_id: int,
    payload: ThesisReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    thesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
    if thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found")

    group = db.query(Group).filter(Group.id == thesis.group_id).first()
    supervisor = (
        db.query(Supervisor).filter(Supervisor.user_id == current_user.id).first()
    )
    if (
        group is None
        or supervisor is None
        or group.assigned_supervisor_id != supervisor.id
    ):
        raise HTTPException(
            status_code=403, detail="You are not the supervisor for this group"
        )

    if thesis.status != "pending":
        raise HTTPException(
            status_code=400, detail="This thesis is not awaiting review"
        )

    if payload.action == "approve":
        thesis.status = "approved"
        db.commit()
        return MessageResponse(message="Thesis approved. Awaiting admin publish.")

    elif payload.action == "revise":
        if not payload.feedback:
            raise HTTPException(
                status_code=400, detail="Feedback is required to request revision"
            )
        thesis.status = "revision_requested"
        thesis.feedback = payload.feedback
        db.commit()
        return MessageResponse(message="Revision requested")

    elif payload.action == "escalate":
        if not payload.feedback:
            raise HTTPException(
                status_code=400, detail="A reason is required to escalate"
            )
        thesis.status = "escalated"
        thesis.feedback = payload.feedback
        db.commit()

        notify_admins(
            db,
            "ProjectSphere: Thesis escalated by supervisor",
            f"<p>Group {group.id} thesis escalated. Reason: {payload.feedback}</p>",
        )
        return MessageResponse(message="Thesis escalated to admin")

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@router.post("/admin/theses/{thesis_id}/action", response_model=MessageResponse)
def admin_thesis_action(
    thesis_id: int,
    payload: AdminThesisActionRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    thesis = db.query(Thesis).filter(Thesis.id == thesis_id).first()
    if thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found")

    if payload.action == "reject_hold":
        thesis.status = "rejected"
        db.commit()
        return MessageResponse(message="Thesis rejected/held by admin")

    elif payload.action == "publish":
        if thesis.status != "approved":
            raise HTTPException(
                status_code=400, detail="Only approved theses can be published"
            )
        thesis.is_published = True
        db.commit()
        return MessageResponse(message="Thesis published")

    elif payload.action == "unpublish":
        thesis.is_published = False
        db.commit()
        return MessageResponse(message="Thesis unpublished")

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@router.get("/theses/repository", response_model=list[ThesisInfo])
def thesis_repository(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Public repository — THESIS submissions only."""
    return (
        db.query(Thesis)
        .filter(Thesis.is_published == True, Thesis.category == "thesis")  # noqa: E712
        .all()
    )


@router.get("/projects/repository", response_model=list[ThesisInfo])
def project_repository(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Public repository — PROJECT submissions only."""
    return (
        db.query(Thesis)
        .filter(Thesis.is_published == True, Thesis.category == "project")  # noqa: E712
        .all()
    )
