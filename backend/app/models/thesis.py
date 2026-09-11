from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class Thesis(Base):
    __tablename__ = "theses"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    category: Mapped[str] = mapped_column(String(20))  # "thesis" or "project"
    manuscript_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    delete_warning_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
