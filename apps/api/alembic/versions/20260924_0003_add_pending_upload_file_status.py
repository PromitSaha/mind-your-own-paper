"""add pending upload file status

Revision ID: 20260924_0003
Revises: 20260923_0002
Create Date: 2026-09-24

"""

from collections.abc import Sequence

from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260924_0003"
down_revision: str | Sequence[str] | None = "20260923_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


file_status = postgresql.ENUM(
    "PENDING_UPLOAD",
    "UPLOADED",
    "PROCESSING",
    "READY",
    "FAILED",
    name="file_status",
    create_type=False,
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE file_status ADD VALUE IF NOT EXISTS 'PENDING_UPLOAD'")

    op.alter_column(
        "files",
        "status",
        server_default="PENDING_UPLOAD",
        existing_type=file_status,
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "files",
        "status",
        server_default="UPLOADED",
        existing_type=file_status,
        existing_nullable=False,
    )
