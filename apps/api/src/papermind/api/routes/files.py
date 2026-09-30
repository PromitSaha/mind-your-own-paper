import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser
from papermind.core.config import Settings, get_settings
from papermind.db.session import get_db
from papermind.models import File, FileStatus, Folder
from papermind.schemas.file import (
    PDF_CONTENT_TYPE,
    PRESIGNED_UPLOAD_EXPIRES_IN_SECONDS,
    FileDownloadUrlResponse,
    FileRead,
    FileUploadCompleteResponse,
    FileUploadInitiateRequest,
    FileUploadInitiateResponse,
)
from papermind.services.s3 import (
    S3ConfigurationError,
    S3ObjectMetadata,
    S3ObjectNotFoundError,
    S3OperationError,
    S3Service,
    get_s3_service,
)
from papermind.services.users import get_user_for_current_auth

router = APIRouter()
PRESIGNED_DOWNLOAD_EXPIRES_IN_SECONDS = 300


def get_configured_s3_service() -> S3Service:
    try:
        return get_s3_service()
    except S3ConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 storage is not configured.",
        ) from error


@router.post(
    "/folders/{folder_id}/files/uploads",
    response_model=FileUploadInitiateResponse,
    status_code=status.HTTP_201_CREATED,
)
def initiate_file_upload(
    folder_id: uuid.UUID,
    payload: FileUploadInitiateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    s3_service: Annotated[S3Service, Depends(get_configured_s3_service)],
) -> FileUploadInitiateResponse:
    if payload.size_bytes > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds the maximum upload size.",
        )

    user = get_user_for_current_auth(session, current_user)
    folder = _get_owned_folder(session, folder_id, user.id)
    if settings.s3_bucket is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 storage is not configured.",
        )

    file_id = uuid.uuid4()
    s3_key = _build_original_pdf_s3_key(folder.id, file_id)
    file = File(
        id=file_id,
        folder_id=folder.id,
        original_filename=payload.filename,
        s3_bucket=settings.s3_bucket,
        s3_key=s3_key,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        status=FileStatus.PENDING_UPLOAD,
    )
    session.add(file)

    try:
        upload_url = s3_service.generate_presigned_upload_url(
            s3_key,
            payload.content_type,
            expires_in=PRESIGNED_UPLOAD_EXPIRES_IN_SECONDS,
        )
        session.commit()
    except (S3ConfigurationError, S3OperationError) as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not initialize file upload.",
        ) from error

    return FileUploadInitiateResponse(
        file_id=file.id,
        filename=file.original_filename,
        status=file.status,
        upload_url=upload_url,
        expires_in=PRESIGNED_UPLOAD_EXPIRES_IN_SECONDS,
    )


@router.get("/folders/{folder_id}/files", response_model=list[FileRead])
def list_folder_files(
    folder_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> list[File]:
    user = get_user_for_current_auth(session, current_user)
    folder = _get_owned_folder(session, folder_id, user.id)
    return list(
        session.scalars(
            select(File)
            .where(
                File.folder_id == folder.id,
                File.is_deleted.is_(False),
            )
            .order_by(File.created_at.desc())
        )
    )


@router.get("/files/{file_id}/download-url", response_model=FileDownloadUrlResponse)
def get_file_download_url(
    file_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
    s3_service: Annotated[S3Service, Depends(get_configured_s3_service)],
) -> FileDownloadUrlResponse:
    user = get_user_for_current_auth(session, current_user)
    file = _get_owned_file(session, file_id, user.id)

    if file.status == FileStatus.PENDING_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File upload has not been verified yet.",
        )

    try:
        download_url = s3_service.generate_presigned_download_url(
            file.s3_key,
            expires_in=PRESIGNED_DOWNLOAD_EXPIRES_IN_SECONDS,
        )
    except S3OperationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create file download URL.",
        ) from error

    return FileDownloadUrlResponse(
        file_id=file.id,
        download_url=download_url,
        expires_in=PRESIGNED_DOWNLOAD_EXPIRES_IN_SECONDS,
    )


@router.post(
    "/files/{file_id}/complete",
    response_model=FileUploadCompleteResponse,
)
def complete_file_upload(
    file_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
    s3_service: Annotated[S3Service, Depends(get_configured_s3_service)],
) -> FileUploadCompleteResponse:
    user = get_user_for_current_auth(session, current_user)
    file = _get_owned_file(session, file_id, user.id)

    if file.status == FileStatus.UPLOADED:
        return _to_complete_response(file)

    if file.status != FileStatus.PENDING_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File upload cannot be completed from its current status.",
        )

    metadata = _get_s3_metadata_or_http_error(s3_service, file.s3_key)
    _verify_s3_metadata(file, metadata)

    file.status = FileStatus.UPLOADED
    session.commit()
    session.refresh(file)
    return _to_complete_response(file)


def _get_owned_folder(
    session: Session,
    folder_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Folder:
    folder = session.scalar(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.owner_id == user_id,
            Folder.is_deleted.is_(False),
        )
    )
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found.",
        )
    return folder


def _get_owned_file(session: Session, file_id: uuid.UUID, user_id: uuid.UUID) -> File:
    file = session.scalar(
        select(File)
        .join(File.folder)
        .where(
            File.id == file_id,
            File.is_deleted.is_(False),
            Folder.owner_id == user_id,
            Folder.is_deleted.is_(False),
        )
    )
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
    return file


def _build_original_pdf_s3_key(folder_id: uuid.UUID, file_id: uuid.UUID) -> str:
    return f"folders/{folder_id}/files/{file_id}/original.pdf"


def _get_s3_metadata_or_http_error(
    s3_service: S3Service,
    s3_key: str,
) -> S3ObjectMetadata:
    try:
        return s3_service.get_object_metadata(s3_key)
    except S3ObjectNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Uploaded file was not found in S3.",
        ) from error
    except S3OperationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify uploaded file.",
        ) from error


def _verify_s3_metadata(file: File, metadata: S3ObjectMetadata) -> None:
    if metadata.content_length != file.size_bytes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Uploaded file size does not match the expected size.",
        )

    if metadata.content_type != PDF_CONTENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Uploaded file content type is not supported.",
        )


def _to_complete_response(file: File) -> FileUploadCompleteResponse:
    return FileUploadCompleteResponse(
        file_id=file.id,
        filename=file.original_filename,
        status=file.status,
    )
