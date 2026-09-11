from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    student_id: Mapped[str] = mapped_column(String(50), unique=True)
    department: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(10))  # e.g. "4"
    term: Mapped[str] = mapped_column(String(10))  # e.g. "1"
    section: Mapped[str] = mapped_column(String(10))  # e.g. "A"
