from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class Supervisor(Base):
    __tablename__ = "supervisors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    department: Mapped[str] = mapped_column(String(100))
    research_areas: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int] = mapped_column(Integer, default=3)
    capacity_override: Mapped[int] = mapped_column(Integer, default=0)


class SupervisorPreference(Base):
    __tablename__ = "supervisor_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    supervisor_id: Mapped[int] = mapped_column(ForeignKey("supervisors.id"))
    preference_rank: Mapped[int] = mapped_column()
