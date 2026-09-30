from typing import Any

import pytest
from botocore.exceptions import ClientError

from papermind.core.config import Settings
from papermind.services import s3 as s3_module
from papermind.services.s3 import (
    S3ConfigurationError,
    S3ObjectNotFoundError,
    S3OperationError,
    S3Service,
)


def build_settings(
    s3_bucket: str | None = "papermind-dev-8086",
    aws_profile: str | None = None,
) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://user:password@localhost:5432/papermind",
        aws_region="us-east-2",
        s3_bucket=s3_bucket,
        AWS_PROFILE=aws_profile,
    )


class FakeS3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.head_response: dict[str, Any] = {
            "ContentLength": 1234,
            "ContentType": "application/pdf",
            "ETag": '"abc123"',
        }
        self.head_error: Exception | None = None

    def generate_presigned_url(
        self,
        client_method: str,
        *,
        Params: dict[str, Any],
        ExpiresIn: int,
        HttpMethod: str,
    ) -> str:
        self.calls.append(
            (
                "generate_presigned_url",
                {
                    "client_method": client_method,
                    "Params": Params,
                    "ExpiresIn": ExpiresIn,
                    "HttpMethod": HttpMethod,
                },
            ),
        )
        return f"https://signed.example/{client_method}"

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self.calls.append(("head_object", {"Bucket": Bucket, "Key": Key}))
        if self.head_error is not None:
            raise self.head_error
        return self.head_response

    def delete_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self.calls.append(("delete_object", {"Bucket": Bucket, "Key": Key}))
        return {}


def make_client_error(code: str, status_code: int) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": "S3 error"},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        },
        "HeadObject",
    )


def test_s3_service_builds_regional_s3v4_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs: dict[str, Any] = {}
    fake_client = FakeS3Client()

    def fake_boto3_client(service_name: str, **kwargs: Any) -> FakeS3Client:
        captured_kwargs["service_name"] = service_name
        captured_kwargs.update(kwargs)
        return fake_client

    monkeypatch.setattr(s3_module.boto3, "client", fake_boto3_client)

    service = S3Service(settings=build_settings())

    assert service._client is fake_client
    assert captured_kwargs["service_name"] == "s3"
    assert captured_kwargs["region_name"] == "us-east-2"
    assert captured_kwargs["endpoint_url"] == "https://s3.us-east-2.amazonaws.com"
    assert captured_kwargs["config"].signature_version == "s3v4"


def test_s3_service_uses_configured_aws_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_profile: dict[str, str] = {}
    captured_kwargs: dict[str, Any] = {}
    fake_client = FakeS3Client()

    class FakeSession:
        def __init__(self, *, profile_name: str) -> None:
            captured_profile["profile_name"] = profile_name

        def client(self, service_name: str, **kwargs: Any) -> FakeS3Client:
            captured_kwargs["service_name"] = service_name
            captured_kwargs.update(kwargs)
            return fake_client

    monkeypatch.setattr(s3_module.boto3, "Session", FakeSession)

    service = S3Service(settings=build_settings(aws_profile="papermind-dev"))

    assert service._client is fake_client
    assert captured_profile["profile_name"] == "papermind-dev"
    assert captured_kwargs["service_name"] == "s3"
    assert captured_kwargs["region_name"] == "us-east-2"


def test_s3_service_requires_bucket_setting() -> None:
    with pytest.raises(S3ConfigurationError):
        S3Service(settings=build_settings(s3_bucket=None), client=FakeS3Client())


def test_generate_presigned_upload_url_signs_bucket_key_and_content_type() -> None:
    fake_client = FakeS3Client()
    service = S3Service(settings=build_settings(), client=fake_client)

    url = service.generate_presigned_upload_url(
        "folders/folder-id/files/file-id.pdf",
        "application/pdf",
    )

    assert url == "https://signed.example/put_object"
    assert fake_client.calls == [
        (
            "generate_presigned_url",
            {
                "client_method": "put_object",
                "Params": {
                    "Bucket": "papermind-dev-8086",
                    "Key": "folders/folder-id/files/file-id.pdf",
                    "ContentType": "application/pdf",
                },
                "ExpiresIn": 300,
                "HttpMethod": "PUT",
            },
        ),
    ]


def test_generate_presigned_download_url_signs_bucket_and_key() -> None:
    fake_client = FakeS3Client()
    service = S3Service(settings=build_settings(), client=fake_client)

    url = service.generate_presigned_download_url(
        "folders/folder-id/files/file-id.pdf",
        expires_in=120,
    )

    assert url == "https://signed.example/get_object"
    assert fake_client.calls == [
        (
            "generate_presigned_url",
            {
                "client_method": "get_object",
                "Params": {
                    "Bucket": "papermind-dev-8086",
                    "Key": "folders/folder-id/files/file-id.pdf",
                },
                "ExpiresIn": 120,
                "HttpMethod": "GET",
            },
        ),
    ]


def test_get_object_metadata_returns_app_friendly_metadata() -> None:
    fake_client = FakeS3Client()
    service = S3Service(settings=build_settings(), client=fake_client)

    metadata = service.get_object_metadata("folders/folder-id/files/file-id.pdf")

    assert metadata.content_length == 1234
    assert metadata.content_type == "application/pdf"
    assert metadata.etag == '"abc123"'


def test_get_object_metadata_distinguishes_not_found_errors() -> None:
    fake_client = FakeS3Client()
    fake_client.head_error = make_client_error("404", 404)
    service = S3Service(settings=build_settings(), client=fake_client)

    with pytest.raises(S3ObjectNotFoundError):
        service.get_object_metadata("missing.pdf")


def test_get_object_metadata_wraps_unexpected_aws_errors() -> None:
    fake_client = FakeS3Client()
    fake_client.head_error = make_client_error("AccessDenied", 403)
    service = S3Service(settings=build_settings(), client=fake_client)

    with pytest.raises(S3OperationError):
        service.get_object_metadata("private.pdf")


def test_delete_object_deletes_from_configured_bucket() -> None:
    fake_client = FakeS3Client()
    service = S3Service(settings=build_settings(), client=fake_client)

    service.delete_object("folders/folder-id/files/file-id.pdf")

    assert fake_client.calls == [
        (
            "delete_object",
            {
                "Bucket": "papermind-dev-8086",
                "Key": "folders/folder-id/files/file-id.pdf",
            },
        ),
    ]
