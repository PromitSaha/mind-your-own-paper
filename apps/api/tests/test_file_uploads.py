from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from papermind.api.routes import files as files_module
from papermind.api.routes.files import get_configured_s3_service
from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser
from papermind.core.config import Settings, get_settings
from papermind.db.base import Base
from papermind.db.session import get_db
from papermind.main import create_app
from papermind.models import File, FileStatus, Folder, User
from papermind.services.s3 import (
    S3ConfigurationError,
    S3ObjectMetadata,
    S3ObjectNotFoundError,
)


class FakeS3Service:
    def __init__(self) -> None:
        self.upload_url = "https://signed.example/upload"
        self.upload_calls: list[tuple[str, str, int]] = []
        self.metadata = S3ObjectMetadata(
            content_length=1024,
            content_type="application/pdf",
            etag='"etag"',
        )
        self.download_url = "https://signed.example/download"
        self.download_calls: list[tuple[str, int]] = []
        self.metadata_error: Exception | None = None
        self.metadata_calls: list[str] = []

    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str,
        expires_in: int = 300,
    ) -> str:
        self.upload_calls.append((s3_key, content_type, expires_in))
        return self.upload_url

    def get_object_metadata(self, s3_key: str) -> S3ObjectMetadata:
        self.metadata_calls.append(s3_key)
        if self.metadata_error is not None:
            raise self.metadata_error
        return self.metadata

    def generate_presigned_download_url(
        self,
        s3_key: str,
        expires_in: int = 300,
    ) -> str:
        self.download_calls.append((s3_key, expires_in))
        return self.download_url


def build_test_client(
    *,
    clerk_user_id: str = "user_test123",
    email: str = "promit@example.com",
    max_upload_size_bytes: int = 50 * 1024 * 1024,
) -> tuple[TestClient, sessionmaker[Session], FakeS3Service]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    fake_s3_service = FakeS3Service()
    app = create_app()

    async def override_current_user() -> CurrentUser:
        return CurrentUser(
            clerk_user_id=clerk_user_id,
            email=email,
            first_name="Promit",
            last_name="Saha",
            image_url=None,
        )

    def override_get_db() -> Generator[Session]:
        with testing_session() as session:
            yield session

    def override_get_settings() -> Settings:
        return Settings(
            database_url="sqlite+pysqlite:///:memory:",
            s3_bucket="papermind-dev-8086",
            max_upload_size_bytes=max_upload_size_bytes,
        )

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    app.dependency_overrides[get_configured_s3_service] = lambda: fake_s3_service
    return TestClient(app), testing_session, fake_s3_service


def sync_test_user(client: TestClient) -> str:
    response = client.get("/auth/me")
    assert response.status_code == 200
    return response.json()["id"]


def create_test_folder(
    testing_session: sessionmaker[Session],
    *,
    user_id: UUID,
    name: str = "Robotics Papers",
) -> UUID:
    with testing_session() as session:
        folder = Folder(owner_id=user_id, name=name)
        session.add(folder)
        session.commit()
        return folder.id


def create_file(
    testing_session: sessionmaker[Session],
    *,
    folder_id: UUID,
    status: FileStatus = FileStatus.PENDING_UPLOAD,
    size_bytes: int = 1024,
    content_type: str = "application/pdf",
) -> UUID:
    with testing_session() as session:
        file = File(
            folder_id=folder_id,
            original_filename="paper.pdf",
            s3_bucket="papermind-dev-8086",
            s3_key="folders/folder-id/files/file-id/original.pdf",
            content_type=content_type,
            size_bytes=size_bytes,
            status=status,
        )
        session.add(file)
        session.commit()
        return file.id


def test_initiate_upload_creates_pending_file_and_presigned_url() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)

    response = client.post(
        f"/folders/{folder_id}/files/uploads",
        json={
            "filename": "paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "paper.pdf"
    assert body["status"] == FileStatus.PENDING_UPLOAD
    assert body["upload_url"] == "https://signed.example/upload"
    assert body["expires_in"] == 300

    file_id = UUID(body["file_id"])
    expected_key = f"folders/{folder_id}/files/{file_id}/original.pdf"
    assert fake_s3_service.upload_calls == [(expected_key, "application/pdf", 300)]

    with testing_session() as session:
        file = session.get(File, file_id)

    assert file is not None
    assert file.folder_id == folder_id
    assert file.s3_bucket == "papermind-dev-8086"
    assert file.s3_key == expected_key
    assert file.status == FileStatus.PENDING_UPLOAD
    assert file.size_bytes == 1024


@pytest.mark.parametrize(
    "payload",
    [
        {
            "filename": "paper.txt",
            "content_type": "text/plain",
            "size_bytes": 1024,
        },
        {
            "filename": "paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 0,
        },
        {
            "filename": "../paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
        {
            "filename": "paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
            "s3_key": "client/chosen/key.pdf",
        },
        {
            "filename": "paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
            "status": "UPLOADED",
        },
    ],
)
def test_initiate_upload_rejects_invalid_payloads(payload: dict[str, object]) -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)

    response = client.post(f"/folders/{folder_id}/files/uploads", json=payload)

    assert response.status_code == 422
    assert fake_s3_service.upload_calls == []


def test_initiate_upload_rejects_oversized_file() -> None:
    client, testing_session, fake_s3_service = build_test_client(
        max_upload_size_bytes=100,
    )
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)

    response = client.post(
        f"/folders/{folder_id}/files/uploads",
        json={
            "filename": "paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 101,
        },
    )

    assert response.status_code == 413
    assert fake_s3_service.upload_calls == []


def test_initiate_upload_rejects_missing_folder() -> None:
    client, _testing_session, fake_s3_service = build_test_client()
    sync_test_user(client)

    response = client.post(
        "/folders/00000000-0000-0000-0000-000000000001/files/uploads",
        json={
            "filename": "paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    )

    assert response.status_code == 404
    assert fake_s3_service.upload_calls == []


def test_initiate_upload_rejects_another_users_folder() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    sync_test_user(client)
    with testing_session() as session:
        other_user = User(
            clerk_user_id="other_user",
            email="other@example.com",
        )
        folder = Folder(owner=other_user, name="Private Folder")
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.post(
        f"/folders/{folder_id}/files/uploads",
        json={
            "filename": "paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    )

    assert response.status_code == 404
    assert fake_s3_service.upload_calls == []


def test_initiate_upload_returns_503_when_s3_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, testing_session, _fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)

    def raise_s3_configuration_error() -> None:
        raise S3ConfigurationError("missing bucket")

    client.app.dependency_overrides.pop(get_configured_s3_service)
    monkeypatch.setattr(
        files_module,
        "get_s3_service",
        raise_s3_configuration_error,
    )

    response = client.post(
        f"/folders/{folder_id}/files/uploads",
        json={
            "filename": "paper.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "S3 storage is not configured."}


def test_list_folder_files_returns_owned_folder_files() -> None:
    client, testing_session, _fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)
    file_id = create_file(
        testing_session,
        folder_id=folder_id,
        status=FileStatus.UPLOADED,
    )

    response = client.get(f"/folders/{folder_id}/files")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(file_id)
    assert body[0]["folder_id"] == str(folder_id)
    assert body[0]["original_filename"] == "paper.pdf"
    assert body[0]["content_type"] == "application/pdf"
    assert body[0]["size_bytes"] == 1024
    assert body[0]["status"] == FileStatus.UPLOADED
    assert body[0]["is_deleted"] is False


def test_list_folder_files_rejects_another_users_folder() -> None:
    client, testing_session, _fake_s3_service = build_test_client()
    sync_test_user(client)
    with testing_session() as session:
        other_user = User(
            clerk_user_id="other_user",
            email="other@example.com",
        )
        folder = Folder(owner=other_user, name="Private Folder")
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.get(f"/folders/{folder_id}/files")

    assert response.status_code == 404


def test_get_file_download_url_returns_presigned_url() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)
    file_id = create_file(
        testing_session,
        folder_id=folder_id,
        status=FileStatus.UPLOADED,
    )

    response = client.get(f"/files/{file_id}/download-url")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": str(file_id),
        "download_url": "https://signed.example/download",
        "expires_in": 300,
    }
    assert fake_s3_service.download_calls == [
        ("folders/folder-id/files/file-id/original.pdf", 300)
    ]


def test_get_file_download_url_rejects_pending_upload() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)
    file_id = create_file(testing_session, folder_id=folder_id)

    response = client.get(f"/files/{file_id}/download-url")

    assert response.status_code == 409
    assert fake_s3_service.download_calls == []


def test_get_file_download_url_rejects_another_users_file() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    sync_test_user(client)
    with testing_session() as session:
        other_user = User(
            clerk_user_id="other_user",
            email="other@example.com",
        )
        folder = Folder(owner=other_user, name="Private Folder")
        file = File(
            folder=folder,
            original_filename="paper.pdf",
            s3_bucket="papermind-dev-8086",
            s3_key="folders/folder-id/files/file-id/original.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            status=FileStatus.UPLOADED,
        )
        session.add(file)
        session.commit()
        file_id = file.id

    response = client.get(f"/files/{file_id}/download-url")

    assert response.status_code == 404
    assert fake_s3_service.download_calls == []


def test_complete_upload_transitions_pending_file_to_uploaded() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)
    file_id = create_file(testing_session, folder_id=folder_id)

    response = client.post(f"/files/{file_id}/complete")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": str(file_id),
        "filename": "paper.pdf",
        "status": FileStatus.UPLOADED,
    }
    assert fake_s3_service.metadata_calls == [
        "folders/folder-id/files/file-id/original.pdf",
    ]

    with testing_session() as session:
        file = session.get(File, file_id)

    assert file is not None
    assert file.status == FileStatus.UPLOADED


def test_complete_upload_keeps_pending_when_s3_object_is_missing() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)
    file_id = create_file(testing_session, folder_id=folder_id)
    fake_s3_service.metadata_error = S3ObjectNotFoundError("missing")

    response = client.post(f"/files/{file_id}/complete")

    assert response.status_code == 409
    with testing_session() as session:
        file = session.get(File, file_id)

    assert file is not None
    assert file.status == FileStatus.PENDING_UPLOAD


@pytest.mark.parametrize(
    "metadata",
    [
        S3ObjectMetadata(
            content_length=999,
            content_type="application/pdf",
            etag='"etag"',
        ),
        S3ObjectMetadata(
            content_length=1024,
            content_type="text/plain",
            etag='"etag"',
        ),
    ],
)
def test_complete_upload_rejects_metadata_mismatch(
    metadata: S3ObjectMetadata,
) -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)
    file_id = create_file(testing_session, folder_id=folder_id)
    fake_s3_service.metadata = metadata

    response = client.post(f"/files/{file_id}/complete")

    assert response.status_code == 409
    with testing_session() as session:
        file = session.get(File, file_id)

    assert file is not None
    assert file.status == FileStatus.PENDING_UPLOAD


def test_complete_upload_rejects_missing_file() -> None:
    client, _testing_session, fake_s3_service = build_test_client()
    sync_test_user(client)

    response = client.post("/files/00000000-0000-0000-0000-000000000001/complete")

    assert response.status_code == 404
    assert fake_s3_service.metadata_calls == []


def test_complete_upload_rejects_another_users_file() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    sync_test_user(client)
    with testing_session() as session:
        other_user = User(
            clerk_user_id="other_user",
            email="other@example.com",
        )
        folder = Folder(owner=other_user, name="Private Folder")
        file = File(
            folder=folder,
            original_filename="paper.pdf",
            s3_bucket="papermind-dev-8086",
            s3_key="folders/folder-id/files/file-id/original.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            status=FileStatus.PENDING_UPLOAD,
        )
        session.add(file)
        session.commit()
        file_id = file.id

    response = client.post(f"/files/{file_id}/complete")

    assert response.status_code == 404
    assert fake_s3_service.metadata_calls == []


@pytest.mark.parametrize(
    "current_status",
    [FileStatus.PROCESSING, FileStatus.READY, FileStatus.FAILED],
)
def test_complete_upload_does_not_reset_later_statuses(
    current_status: FileStatus,
) -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)
    file_id = create_file(
        testing_session,
        folder_id=folder_id,
        status=current_status,
    )

    response = client.post(f"/files/{file_id}/complete")

    assert response.status_code == 409
    assert fake_s3_service.metadata_calls == []
    with testing_session() as session:
        file = session.get(File, file_id)

    assert file is not None
    assert file.status == current_status


def test_complete_upload_is_idempotent_for_uploaded_file() -> None:
    client, testing_session, fake_s3_service = build_test_client()
    user_id = UUID(sync_test_user(client))
    folder_id = create_test_folder(testing_session, user_id=user_id)
    file_id = create_file(
        testing_session,
        folder_id=folder_id,
        status=FileStatus.UPLOADED,
    )

    response = client.post(f"/files/{file_id}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == FileStatus.UPLOADED
    assert fake_s3_service.metadata_calls == []
