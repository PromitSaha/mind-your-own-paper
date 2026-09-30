import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from papermind.models import FileStatus

PDF_CONTENT_TYPE = "application/pdf"
PRESIGNED_UPLOAD_EXPIRES_IN_SECONDS = 300

OriginalFilename = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class FileUploadInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: OriginalFilename
    content_type: str
    size_bytes: int = Field(gt=0)

    @field_validator("filename")
    @classmethod
    def filename_must_not_be_a_path(cls, filename: str) -> str:
        if "/" in filename or "\\" in filename:
            raise ValueError("Filename must not contain path separators.")
        return filename

    @field_validator("content_type")
    @classmethod
    def content_type_must_be_pdf(cls, content_type: str) -> str:
        if content_type != PDF_CONTENT_TYPE:
            raise ValueError("Only application/pdf files are supported.")
        return content_type


class FileUploadInitiateResponse(BaseModel):
    file_id: uuid.UUID
    filename: str
    status: FileStatus
    upload_url: str
    expires_in: int


class FileUploadCompleteResponse(BaseModel):
    file_id: uuid.UUID
    filename: str
    status: FileStatus


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    folder_id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    status: FileStatus
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class FileDownloadUrlResponse(BaseModel):
    file_id: uuid.UUID
    download_url: str
    expires_in: int
