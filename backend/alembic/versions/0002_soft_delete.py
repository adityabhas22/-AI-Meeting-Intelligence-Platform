"""add soft-delete column to meetings

Revision ID: 0002_soft_delete
Revises: 413ee47c6d76
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_soft_delete"
down_revision: str | None = "413ee47c6d76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_meetings_deleted_at", "meetings", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_meetings_deleted_at", table_name="meetings")
    op.drop_column("meetings", "deleted_at")
