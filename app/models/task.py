from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    reference_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )  # supervisor's user id
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Notification tracking - so we don't send the same warning/risk email twice
    warning_sent: Mapped[bool] = mapped_column(default=False)
    risk_sent: Mapped[bool] = mapped_column(default=False)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending / verified / rejected
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
