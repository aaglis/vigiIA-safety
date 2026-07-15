from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

try:  # pragma: no cover - optional runtime dependency
    import boto3
    from botocore.client import Config
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]


class EvidenceStorage(Protocol):
    def ensure_private_bucket(self) -> None: ...
    def presign_upload(self, object_key: str, media_type: str, ttl_seconds: int) -> str: ...
    def presign_download(self, object_key: str, ttl_seconds: int) -> str: ...
    def delete_object(self, object_key: str) -> None: ...


@dataclass
class MockEvidenceStorage:
    bucket_name: str
    public_bucket: bool = False

    def ensure_private_bucket(self) -> None:
        if self.public_bucket:
            raise ValueError("evidence bucket must be private")

    def presign_upload(self, object_key: str, media_type: str, ttl_seconds: int) -> str:
        self.ensure_private_bucket()
        return f"https://s3.mock/{self.bucket_name}/{object_key}?method=PUT&content_type={media_type}&ttl={ttl_seconds}"

    def presign_download(self, object_key: str, ttl_seconds: int) -> str:
        self.ensure_private_bucket()
        return f"https://s3.mock/{self.bucket_name}/{object_key}?method=GET&ttl={ttl_seconds}"

    def delete_object(self, object_key: str) -> None:
        self.ensure_private_bucket()


class MinioEvidenceStorage:
    def __init__(self, bucket_name: str, endpoint_url: str | None = None, access_key: str | None = None, secret_key: str | None = None, region_name: str = "us-east-1") -> None:
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region_name = region_name
        self._client = None

    @property
    def client(self):
        if boto3 is None:
            raise RuntimeError("boto3 is not installed; real MinIO storage unavailable")
        if self._client is None:
            kwargs: dict[str, Any] = {"region_name": self.region_name}
            if self.endpoint_url:
                kwargs["endpoint_url"] = self.endpoint_url
            if Config is not None:
                kwargs["config"] = Config(signature_version="s3v4")
            self._client = boto3.client(
                "s3",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                **kwargs,
            )
        return self._client

    def ensure_private_bucket(self) -> None:
        self.client.head_bucket(Bucket=self.bucket_name)
        acl = self.client.get_bucket_acl(Bucket=self.bucket_name)
        grants = acl.get("Grants", [])
        if any(grant.get("Grantee", {}).get("URI", "").endswith("AllUsers") or grant.get("Permission") == "FULL_CONTROL" and grant.get("Grantee", {}).get("Type") == "Group" for grant in grants):
            raise ValueError("evidence bucket must be private")

    def presign_upload(self, object_key: str, media_type: str, ttl_seconds: int) -> str:
        self.ensure_private_bucket()
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket_name, "Key": object_key, "ContentType": media_type},
            ExpiresIn=ttl_seconds,
        )

    def presign_download(self, object_key: str, ttl_seconds: int) -> str:
        self.ensure_private_bucket()
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=ttl_seconds,
        )

    def delete_object(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=object_key)


def default_evidence_storage(settings_obj: object) -> EvidenceStorage:
    app_env = getattr(settings_obj, "app_env", "dev")
    bucket_name = getattr(settings_obj, "evidence_bucket_name", "vigia-evidence-private")
    endpoint_url = getattr(settings_obj, "s3_endpoint_url", None)
    access_key = getattr(settings_obj, "minio_access_key", None) or getattr(settings_obj, "s3_access_key_id", None)
    secret_key = getattr(settings_obj, "minio_secret_key", None) or getattr(settings_obj, "s3_secret_access_key", None)
    region_name = getattr(settings_obj, "s3_region", "us-east-1")
    if app_env.lower() in {"production", "staging"}:
        if not endpoint_url:
            raise RuntimeError("s3_endpoint_url is required in staging/production")
        if boto3 is None:
            raise RuntimeError("real evidence storage required in staging/production but boto3 is unavailable")
        return MinioEvidenceStorage(bucket_name=bucket_name, endpoint_url=endpoint_url, access_key=access_key, secret_key=secret_key, region_name=region_name)
    return MockEvidenceStorage(bucket_name=bucket_name)
