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
    def __init__(self, bucket_name: str, endpoint_url: str | None = None, access_key: str | None = None, secret_key: str | None = None, region_name: str = "us-east-1", public_endpoint_url: str | None = None) -> None:
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.public_endpoint_url = public_endpoint_url or endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region_name = region_name
        self._client = None
        self._public_client = None

    def _build_client(self, endpoint_url: str | None):
        if boto3 is None:
            raise RuntimeError("boto3 is not installed; real MinIO storage unavailable")
        kwargs: dict[str, Any] = {"region_name": self.region_name}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if Config is not None:
            kwargs["config"] = Config(signature_version="s3v4")
        return boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            **kwargs,
        )

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client(self.endpoint_url)
        return self._client

    @property
    def public_client(self):
        """Client cujo endpoint é o host alcançável pelo navegador (assina as URLs de download)."""
        if self.public_endpoint_url == self.endpoint_url:
            return self.client
        if self._public_client is None:
            self._public_client = self._build_client(self.public_endpoint_url)
        return self._public_client

    def ensure_private_bucket(self) -> None:
        self.client.head_bucket(Bucket=self.bucket_name)
        acl = self.client.get_bucket_acl(Bucket=self.bucket_name)
        grants = acl.get("Grants", [])
        if any(grant.get("Grantee", {}).get("URI", "").endswith("AllUsers") or grant.get("Permission") == "FULL_CONTROL" and grant.get("Grantee", {}).get("Type") == "Group" for grant in grants):
            raise ValueError("evidence bucket must be private")

    def presign_upload(self, object_key: str, media_type: str, ttl_seconds: int) -> str:
        self.ensure_private_bucket()
        # ContentType fora da assinatura: o cliente envia o header Content-Type no PUT
        # (o MinIO grava esse valor) sem risco de SignatureDoesNotMatch por mismatch.
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=ttl_seconds,
        )

    def presign_download(self, object_key: str, ttl_seconds: int) -> str:
        self.ensure_private_bucket()
        return self.public_client.generate_presigned_url(
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
    public_endpoint_url = getattr(settings_obj, "s3_public_endpoint_url", None)
    access_key = getattr(settings_obj, "minio_access_key", None) or getattr(settings_obj, "s3_access_key_id", None)
    secret_key = getattr(settings_obj, "minio_secret_key", None) or getattr(settings_obj, "s3_secret_access_key", None)
    region_name = getattr(settings_obj, "s3_region", "us-east-1")
    strict = app_env.lower() in {"production", "staging"}
    if strict and not endpoint_url:
        raise RuntimeError("s3_endpoint_url is required in staging/production")
    # Usa MinIO/S3 real sempre que houver endpoint configurado + boto3 disponível
    # (inclusive em dev). Sem endpoint, cai no mock. Em prod/staging o real é obrigatório.
    if endpoint_url and boto3 is not None:
        return MinioEvidenceStorage(bucket_name=bucket_name, endpoint_url=endpoint_url, access_key=access_key, secret_key=secret_key, region_name=region_name, public_endpoint_url=public_endpoint_url)
    if strict:
        raise RuntimeError("real evidence storage required in staging/production but boto3 is unavailable")
    return MockEvidenceStorage(bucket_name=bucket_name)
