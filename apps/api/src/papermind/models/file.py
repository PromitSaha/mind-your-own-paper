import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from papermind.db.base import Base

if TYPE_CHECKING:
    from papermind.models.folder import Folder


class FileStatus(enum.StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_files_size_bytes_non_negative"),
        UniqueConstraint("s3_bucket", "s3_key", name="uq_files_s3_bucket_s3_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    folder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"),
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    s3_bucket: Mapped[str] = mapped_column(String(255))
    s3_key: Mapped[str] = mapped_column(String(1024))
    content_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[FileStatus] = mapped_column(
        Enum(FileStatus, name="file_status"),
        default=FileStatus.UPLOADED,
        server_default=FileStatus.UPLOADED.value,
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    folder: Mapped["Folder"] = relationship(back_populates="files")
