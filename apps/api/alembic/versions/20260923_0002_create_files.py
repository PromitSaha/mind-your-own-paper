"""create files

Revision ID: 20260923_0002
Revises: 20260923_0001
Create Date: 2026-09-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260923_0002"
down_revision: str | Sequence[str] | None = "20260923_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


file_status = postgresql.ENUM(
    "UPLOADED",
    "PROCESSING",
    "READY",
    "FAILED",
    name="file_status",
    create_type=False,
)


def upgrade() -> None:
    file_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("s3_bucket", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            file_status,
            server_default="UPLOADED",
            nullable=False,
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_files_size_bytes_non_negative",
        ),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("s3_bucket", "s3_key", name="uq_files_s3_bucket_s3_key"),
    )
    op.create_index(op.f("ix_files_folder_id"), "files", ["folder_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_files_folder_id"), table_name="files")
    op.drop_table("files")
    file_status.drop(op.get_bind(), checkfirst=True)
