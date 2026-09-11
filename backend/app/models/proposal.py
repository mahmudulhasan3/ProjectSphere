from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending / approved / rejected
    approved_topic_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "proposal_topics.id",
            use_alter=True,
            name="fk_proposals_approved_topic_id",
        ),
        nullable=True,
    )
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    resubmission_deadline: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    suggested_area: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProposalTopic(Base):
    __tablename__ = "proposal_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"))
    title: Mapped[str] = mapped_column(String(255))
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    assigned_by_supervisor: Mapped[bool] = mapped_column(default=False)
