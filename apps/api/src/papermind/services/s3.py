from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, ProfileNotFound

from papermind.core.config import Settings, get_settings


class S3ServiceError(Exception):
    """Base exception for PaperMind S3 operations."""


class S3ConfigurationError(S3ServiceError):
    """Raised when S3 settings are incomplete."""


class S3ObjectNotFoundError(S3ServiceError):
    """Raised when the requested S3 object does not exist."""


class S3OperationError(S3ServiceError):
    """Raised when AWS rejects or cannot complete an S3 operation."""


@dataclass(frozen=True)
class S3ObjectMetadata:
    content_length: int
    content_type: str | None
    etag: str | None


class S3Service:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        if self._settings.s3_bucket is None:
            raise S3ConfigurationError("PAPERMIND_S3_BUCKET is required.")

        self._bucket = self._settings.s3_bucket
        self._client = client or self._build_client()

    def _build_client(self) -> Any:
        client_factory = boto3
        if self._settings.aws_profile is not None:
            try:
                client_factory = boto3.Session(profile_name=self._settings.aws_profile)
            except ProfileNotFound as error:
                raise S3ConfigurationError(
                    f"AWS profile {self._settings.aws_profile!r} was not found."
                ) from error

        return client_factory.client(
            "s3",
            region_name=self._settings.aws_region,
            endpoint_url=f"https://s3.{self._settings.aws_region}.amazonaws.com",
            config=Config(signature_version="s3v4"),
        )

    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str,
        expires_in: int = 300,
    ) -> str:
        try:
            return self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
                HttpMethod="PUT",
            )
        except (BotoCoreError, ClientError) as error:
            raise S3OperationError("Could not create S3 upload URL.") from error

    def generate_presigned_download_url(
        self,
        s3_key: str,
        expires_in: int = 300,
    ) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": s3_key},
                ExpiresIn=expires_in,
                HttpMethod="GET",
            )
        except (BotoCoreError, ClientError) as error:
            raise S3OperationError("Could not create S3 download URL.") from error

    def get_object_metadata(self, s3_key: str) -> S3ObjectMetadata:
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=s3_key)
        except ClientError as error:
            if _is_not_found_error(error):
                raise S3ObjectNotFoundError("S3 object was not found.") from error
            raise S3OperationError("Could not fetch S3 object metadata.") from error
        except BotoCoreError as error:
            raise S3OperationError("Could not fetch S3 object metadata.") from error

        return S3ObjectMetadata(
            content_length=response["ContentLength"],
            content_type=response.get("ContentType"),
            etag=response.get("ETag"),
        )

    def delete_object(self, s3_key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=s3_key)
        except (BotoCoreError, ClientError) as error:
            raise S3OperationError("Could not delete S3 object.") from error


def _is_not_found_error(error: ClientError) -> bool:
    error_response = error.response
    error_code = error_response.get("Error", {}).get("Code")
    http_status = error_response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return error_code in {"404", "NoSuchKey", "NotFound"} or http_status == 404


@lru_cache
def get_s3_service() -> S3Service:
    return S3Service()
