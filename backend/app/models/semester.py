from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))  # e.g. "Fall 2026"
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    group_formation_deadline: Mapped[datetime] = mapped_column(DateTime)
    final_submission_deadline: Mapped[datetime] = mapped_column(DateTime)
    auto_delete_days: Mapped[int] = mapped_column(
        Integer, default=30
    )  # for unapproved theses
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
