from datetime import datetime

from sqlalchemy import String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    join_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    leader_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    interested_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assigned_supervisor_id: Mapped[int | None] = mapped_column(
        ForeignKey("supervisors.id"), nullable=True
    )

    # Admin override: if set, this group's final deadline is this date instead of the semester's
    deadline_extension: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    member_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_risk: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
