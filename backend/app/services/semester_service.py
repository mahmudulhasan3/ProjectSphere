from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.models.semester import Semester
from backend.app.models.group import Group


def get_active_semester(db: Session) -> Semester | None:
    return db.query(Semester).filter(Semester.is_active == True).first()  # noqa: E712


def get_effective_deadline(db: Session, group: Group) -> datetime | None:
    """A group's own deadline_extension overrides the active semester's final_submission_deadline."""
    if group.deadline_extension is not None:
        return group.deadline_extension

    semester = get_active_semester(db)
    if semester is None:
        return None
    return semester.final_submission_deadline


def is_past_final_deadline(db: Session, group: Group) -> bool:
    deadline = get_effective_deadline(db, group)
    if deadline is None:
        return False
    return datetime.now(timezone.utc) > deadline.replace(tzinfo=timezone.utc)
