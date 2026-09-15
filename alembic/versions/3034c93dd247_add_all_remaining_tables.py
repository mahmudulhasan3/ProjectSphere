"""add all remaining tables

Revision ID: 3034c93dd247
Revises: ec69db28ac70
Create Date: 2026-09-10 13:33:41.227596

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3034c93dd247"
down_revision: Union[str, Sequence[str], None] = "ec69db28ac70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "semesters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("group_formation_deadline", sa.DateTime(), nullable=False),
        sa.Column("final_submission_deadline", sa.DateTime(), nullable=False),
        sa.Column("auto_delete_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "supervisors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("research_areas", sa.String(length=255), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("capacity_override", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("join_code", sa.String(length=10), nullable=False),
        sa.Column("leader_id", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("interested_area", sa.String(length=100), nullable=True),
        sa.Column("assigned_supervisor_id", sa.Integer(), nullable=True),
        sa.Column("deadline_extension", sa.DateTime(), nullable=True),
        sa.Column("member_risk", sa.Boolean(), nullable=False),
        sa.Column("progress_risk", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["assigned_supervisor_id"],
            ["supervisors.id"],
        ),
        sa.ForeignKeyConstraint(
            ["leader_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_groups_join_code"), "groups", ["join_code"], unique=True)

    op.create_table(
        "group_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id"),
    )

    op.create_table(
        "supervisor_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("supervisor_id", sa.Integer(), nullable=False),
        sa.Column("preference_rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.ForeignKeyConstraint(
            ["supervisor_id"],
            ["supervisors.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # proposals created WITHOUT the approved_topic_id foreign key for now —
    # proposal_topics doesn't exist yet (circular dependency between the two tables)
    op.create_table(
        "proposals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_topic_id", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "proposal_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proposal_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["proposals.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Now both tables exist — add the FK that closes the circular reference
    op.create_foreign_key(
        "fk_proposals_approved_topic_id",
        "proposals",
        "proposal_topics",
        ["approved_topic_id"],
        ["id"],
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("deadline", sa.DateTime(), nullable=False),
        sa.Column("reference_file_url", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("warning_sent", sa.Boolean(), nullable=False),
        sa.Column("risk_sent", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "theses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("manuscript_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("submitted_by", sa.Integer(), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=True),
        sa.Column("github_url", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("submissions")
    op.drop_table("theses")
    op.drop_table("tasks")
    op.drop_constraint(
        "fk_proposals_approved_topic_id", "proposals", type_="foreignkey"
    )
    op.drop_table("proposal_topics")
    op.drop_table("proposals")
    op.drop_table("supervisor_preferences")
    op.drop_table("group_members")
    op.drop_index(op.f("ix_groups_join_code"), table_name="groups")
    op.drop_table("groups")
    op.drop_table("supervisors")
    op.drop_table("semesters")
