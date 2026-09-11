from datetime import datetime, timezone
from backend.app.models.proposal import Proposal
from backend.app.services.notification_service import get_group_member_emails
from backend.app.core.email import send_task_created_email, send_evidence_submitted_email
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.group import Group, GroupMember
from backend.app.models.supervisor import Supervisor
from backend.app.models.task import Task, Submission
from backend.app.services.file_service import save_upload_file
from backend.app.schemas.task import (
    TaskCreateRequest,
    TaskInfo,
    SubmissionInfo,
    SubmissionReviewRequest,
    ProgressResponse,
    MessageResponse,
)

router = APIRouter(tags=["Task"])


def get_user_group(db: Session, user_id: int) -> GroupMember | None:
    return db.query(GroupMember).filter(GroupMember.student_id == user_id).first()


def get_supervisor_profile(db: Session, user_id: int) -> Supervisor | None:
    return db.query(Supervisor).filter(Supervisor.user_id == user_id).first()


def require_supervisor_owns_group(
    db: Session, current_user: User, group_id: int
) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    supervisor = get_supervisor_profile(db, current_user.id)
    if supervisor is None or group.assigned_supervisor_id != supervisor.id:
        raise HTTPException(
            status_code=403, detail="You are not the supervisor for this group"
        )

    return group


# --- Supervisor: create a task for a group ---


@router.post("/groups/{group_id}/tasks", response_model=TaskInfo)
def create_task(
    group_id: int,
    title: str = Form(...),
    description: str = Form(...),
    deadline: datetime = Form(...),
    reference_file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    require_supervisor_owns_group(db, current_user, group_id)

    latest_proposal = (
        db.query(Proposal)
        .filter(Proposal.group_id == group_id)
        .order_by(Proposal.round_number.desc())
        .first()
    )
    if latest_proposal is None or latest_proposal.status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Tasks can only be assigned after the group's proposal is approved",
        )

    file_url = None
    if reference_file is not None:
        file_url = save_upload_file(reference_file, subfolder=f"tasks/{group_id}")

    task = Task(
        group_id=group_id,
        title=title,
        description=description,
        deadline=deadline,
        reference_file_url=file_url,
        created_by=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    for email in get_group_member_emails(db, group_id):
        send_task_created_email(email, task.title, str(task.deadline))

    return task


# --- Supervisor: edit a task (including extending its own deadline) ---


@router.patch("/tasks/{task_id}", response_model=TaskInfo)
def update_task(
    task_id: int,
    title: str | None = Form(None),
    description: str | None = Form(None),
    deadline: datetime | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    require_supervisor_owns_group(db, current_user, task.group_id)

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if deadline is not None:
        task.deadline = deadline
        # Deadline changed - allow warning/risk emails to be sent again
        task.warning_sent = False
        task.risk_sent = False

    db.commit()
    db.refresh(task)

    return task


# --- Student: view tasks for their group ---


@router.get("/groups/{group_id}/tasks", response_model=list[TaskInfo])
def list_group_tasks(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_user_group(db, current_user.id)
    if membership is None or membership.group_id != group_id:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    return db.query(Task).filter(Task.group_id == group_id).all()


# --- Student: submit evidence for a task ---


@router.post("/tasks/{task_id}/submit", response_model=SubmissionInfo)
def submit_evidence(
    task_id: int,
    github_url: str | None = Form(None),
    notes: str | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    membership = get_user_group(db, current_user.id)
    if membership is None or membership.group_id != task.group_id:
        raise HTTPException(status_code=403, detail="Not a member of this task's group")

    file_url = None
    if file is not None:
        file_url = save_upload_file(file, subfolder=f"submissions/{task.group_id}")

    submission = Submission(
        task_id=task_id,
        submitted_by=current_user.id,
        file_url=file_url,
        github_url=github_url,
        notes=notes,
        status="pending",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    group = db.query(Group).filter(Group.id == task.group_id).first()
    if group and group.assigned_supervisor_id:
        supervisor = (
            db.query(Supervisor)
            .filter(Supervisor.id == group.assigned_supervisor_id)
            .first()
        )
        if supervisor:
            sup_user = db.query(User).filter(User.id == supervisor.user_id).first()
            if sup_user:
                send_evidence_submitted_email(
                    sup_user.email, task.title, group.name or f"Group {group.id}"
                )

    return submission


# --- Supervisor: view submissions for a task ---


@router.get("/tasks/{task_id}/submissions", response_model=list[SubmissionInfo])
def list_submissions(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    require_supervisor_owns_group(db, current_user, task.group_id)

    return db.query(Submission).filter(Submission.task_id == task_id).all()


# --- Supervisor: verify or request changes on a submission ---


@router.post("/submissions/{submission_id}/review", response_model=MessageResponse)
def review_submission(
    submission_id: int,
    payload: SubmissionReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    task = db.query(Task).filter(Task.id == submission.task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    require_supervisor_owns_group(db, current_user, task.group_id)

    submission.status = "verified" if payload.approve else "rejected"
    db.commit()

    return MessageResponse(message=f"Submission marked as {submission.status}")


# --- Student: view group's progress % ---


@router.get("/groups/{group_id}/progress", response_model=ProgressResponse)
def get_group_progress(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_user_group(db, current_user.id)
    if membership is None or membership.group_id != group_id:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    tasks = db.query(Task).filter(Task.group_id == group_id).all()
    total = len(tasks)

    if total == 0:
        return ProgressResponse(total_tasks=0, verified_tasks=0, progress_percent=0.0)

    verified = 0
    for task in tasks:
        has_verified_submission = (
            db.query(Submission)
            .filter(Submission.task_id == task.id, Submission.status == "verified")
            .first()
        )
        if has_verified_submission:
            verified += 1

    percent = round((verified / total) * 100, 2)

    return ProgressResponse(
        total_tasks=total, verified_tasks=verified, progress_percent=percent
    )


@router.delete("/tasks/{task_id}", response_model=MessageResponse)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    require_supervisor_owns_group(db, current_user, task.group_id)

    has_submissions = db.query(Submission).filter(Submission.task_id == task_id).first()
    if has_submissions is not None:
        raise HTTPException(
            status_code=400, detail="Cannot delete a task that already has submissions"
        )

    db.delete(task)
    db.commit()

    return MessageResponse(message="Task deleted")
