from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.task import Task, Submission
from app.models.group import Group, GroupMember
from app.models.supervisor import Supervisor
from app.models.user import User
from app.models.thesis import Thesis
from app.core.email import send_email
from app.services.semester_service import get_active_semester

from app.core.email import (
    send_email,
    send_group_at_risk_email,
    send_thesis_delete_warning_email,
)

WARNING_WINDOW = timedelta(days=2)


def get_group_member_emails(db: Session, group_id: int) -> list[str]:
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    emails = []
    for m in members:
        user = db.query(User).filter(User.id == m.student_id).first()
        if user:
            emails.append(user.email)
    return emails


def get_supervisor_email(db: Session, group: Group) -> str | None:
    if group.assigned_supervisor_id is None:
        return None
    supervisor = (
        db.query(Supervisor)
        .filter(Supervisor.id == group.assigned_supervisor_id)
        .first()
    )
    if supervisor is None:
        return None
    user = db.query(User).filter(User.id == supervisor.user_id).first()
    return user.email if user else None


def task_is_complete(db: Session, task_id: int) -> bool:
    verified = (
        db.query(Submission)
        .filter(Submission.task_id == task_id, Submission.status == "verified")
        .first()
    )
    return verified is not None


def check_task_deadlines(db: Session) -> None:
    """Sends warning (~2 days before deadline) and risk (deadline passed) notifications."""
    now = datetime.now(timezone.utc)
    tasks = db.query(Task).all()

    for task in tasks:
        if task_is_complete(db, task.id):
            continue

        deadline = task.deadline.replace(tzinfo=timezone.utc)
        group = db.query(Group).filter(Group.id == task.group_id).first()
        if group is None:
            continue

        if not task.warning_sent and deadline - WARNING_WINDOW <= now < deadline:
            for email in get_group_member_emails(db, group.id):
                send_email(
                    email,
                    f"Deadline approaching: {task.title}",
                    f"<p>Your task '{task.title}' is due soon ({task.deadline}). Please submit your evidence.</p>",
                )
            task.warning_sent = True
            db.commit()

        if not task.risk_sent and now >= deadline:
            recipients = get_group_member_emails(db, group.id)
            supervisor_email = get_supervisor_email(db, group)
            if supervisor_email:
                recipients.append(supervisor_email)

            for email in recipients:
                send_email(
                    email,
                    f"Task overdue: {task.title}",
                    f"<p>The task '{task.title}' for group {group.name} is now overdue and incomplete.</p>",
                )

            task.risk_sent = True
            group.progress_risk = True
            db.commit()


def check_thesis_auto_delete(db: Session) -> None:
    """Warns ~3 days before deletion, then deletes unapproved theses past the semester's auto_delete_days."""
    semester = get_active_semester(db)
    if semester is None:
        return

    now = datetime.now(timezone.utc)
    delete_cutoff = now - timedelta(days=semester.auto_delete_days)
    warning_cutoff = now - timedelta(
        days=max(semester.auto_delete_days - THESIS_DELETE_WARNING_DAYS, 0)
    )

    candidates = db.query(Thesis).filter(Thesis.status != "approved").all()

    for thesis in candidates:
        submitted = thesis.submitted_at.replace(tzinfo=timezone.utc)

        if submitted < delete_cutoff:
            db.delete(thesis)
            continue

        if not thesis.delete_warning_sent and submitted < warning_cutoff:
            group = db.query(Group).filter(Group.id == thesis.group_id).first()
            if group:
                emails = get_group_member_emails(db, group.id)
                days_left = max(
                    (submitted + timedelta(days=semester.auto_delete_days) - now).days,
                    0,
                )
                send_thesis_delete_warning_email(
                    emails, group.name or f"Group {group.id}", days_left
                )
            thesis.delete_warning_sent = True

    db.commit()


def run_all_checks() -> None:
    """Entry point called periodically by the scheduler. Opens its own DB session."""
    db = SessionLocal()
    try:
        check_task_deadlines(db)
        check_thesis_auto_delete(db)
    finally:
        db.close()


THESIS_DELETE_WARNING_DAYS = 3


def notify_admins_group_at_risk(db: Session, group: Group, reason: str) -> None:
    admins = db.query(User).filter(User.role == "admin").all()
    for admin in admins:
        send_group_at_risk_email(admin.email, group.name or f"Group {group.id}", reason)
