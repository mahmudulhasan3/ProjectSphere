"""add is_active to users, delete_warning_sent to theses

Revision ID: 91ca94885436
Revises: 0e6dda2e6640
Create Date: 2026-09-11 14:21:35.175883

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "91ca94885436"
down_revision: Union[str, Sequence[str], None] = "0e6dda2e6640"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default দিয়ে add করছি যাতে existing rows-ও একটা value পায়
    op.add_column(
        "theses",
        sa.Column(
            "delete_warning_sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # migration শেষে DB-level default সরিয়ে দিচ্ছি —
    # future insert-এর value app layer (model/schema default) থেকে আসবে
    op.alter_column("theses", "delete_warning_sent", server_default=None)
    op.alter_column("users", "is_active", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_active")
    op.drop_column("theses", "delete_warning_sent")
