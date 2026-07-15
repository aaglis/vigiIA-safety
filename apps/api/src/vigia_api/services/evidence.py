from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import cast

from ..domain.evidence import EvidenceAccessAuditLog, EvidenceKind, EvidencePurgeError, EvidenceRetentionPolicy, EvidenceSource, IncidentEvidence
from ..settings import settings as global_settings
from ..observability import log_event
from .evidence_storage import EvidenceStorage, default_evidence_storage, MockEvidenceStorage
from .security import generate_token


class InMemoryEvidenceRepository:
    def __init__(self) -> None:
        self.bucket_name = "vigia-evidence-private"
        self.public_bucket = False
        self.default_ttl_seconds = 300
        self.evidence: dict[tuple[str, str, str], IncidentEvidence] = {}
        self.retention_policies: dict[str, EvidenceRetentionPolicy] = {}
        self.audit_logs: list[EvidenceAccessAuditLog] = []


class InMemoryEvidenceMetadataRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, str], dict[str, object]] = {}

    def save(self, evidence: IncidentEvidence) -> None:
        self.rows[(evidence.organization_id, evidence.incident_id, evidence.file_id)] = {
            "organization_id": evidence.organization_id,
            "incident_id": evidence.incident_id,
            "file_id": evidence.file_id,
            "object_key": evidence.object_key,
            "media_type": evidence.media_type,
            "size": evidence.size,
            "source": evidence.source.value,
            "uploaded_by": evidence.uploaded_by,
            "kind": evidence.kind.value,
            "created_at": evidence.created_at,
            "metadata_json": dict(evidence.metadata),
            "deleted_at": evidence.deleted_at,
        }

    def get(self, organization_id: str, incident_id: str, file_id: str) -> dict[str, object] | None:
        return self.rows.get((organization_id, incident_id, file_id))


class EvidenceService:
    def __init__(self, storage: EvidenceStorage | None = None, metadata_repository: object | None = None, settings_obj: object | None = None) -> None:
        config = settings_obj or global_settings
        self.repository = InMemoryEvidenceRepository()
        self.repository.bucket_name = getattr(config, "evidence_bucket_name", "vigia-evidence-private")
        self.repository.default_ttl_seconds = getattr(config, "evidence_presigned_url_ttl_seconds", 300)
        self.storage = storage or default_evidence_storage(config)
        self.metadata_repository = metadata_repository or InMemoryEvidenceMetadataRepository()

    def _save_metadata(self, evidence: IncidentEvidence) -> None:
        save = getattr(self.metadata_repository, "save", None)
        if callable(save):
            save(evidence)

    def _get_metadata(self, organization_id: str, incident_id: str, file_id: str) -> IncidentEvidence | None:
        get = getattr(self.metadata_repository, "get", None)
        if callable(get):
            row = get(organization_id, incident_id, file_id)
            if row is None or isinstance(row, IncidentEvidence):
                return cast(IncidentEvidence | None, row)
            row = cast(dict[str, object], row)
            return IncidentEvidence(
                organization_id=str(row["organization_id"]),
                incident_id=str(row["incident_id"]),
                file_id=str(row["file_id"]),
                object_key=str(row["object_key"]),
                media_type=str(row["media_type"]),
                size=int(cast(int | str, row["size"])),
                source=EvidenceSource(str(row["source"])),
                uploaded_by=str(row["uploaded_by"]),
                kind=EvidenceKind(str(row["kind"])),
                created_at=cast(datetime, row["created_at"]),
                deleted_at=cast(datetime | None, row["deleted_at"]),
                metadata=dict(cast(dict, row["metadata_json"])),
            )
        return None

    def _object_key(self, organization_id: str, incident_id: str, file_id: str) -> str:
        return f"org/{organization_id}/incidents/{incident_id}/evidence/{file_id}"

    def validate_bucket_privacy(self) -> None:
        if self.repository.public_bucket:
            raise ValueError("evidence bucket must be private")
        self.storage.ensure_private_bucket()

    def _audit(self, organization_id: str, actor_user_id: str, action: str, incident_id: str, file_id: str, **metadata: object) -> None:
        self.repository.audit_logs.append(EvidenceAccessAuditLog(id=generate_token(12), organization_id=organization_id, actor_user_id=actor_user_id, action=action, incident_id=incident_id, file_id=file_id, created_at=datetime.now(timezone.utc), metadata={k: v for k, v in metadata.items() if v is not None}))
        append = getattr(self.metadata_repository, "append_audit_log", None)
        if callable(append):
            append(organization_id, actor_user_id, action, incident_id, file_id, metadata=metadata)

    def _find_evidence(self, organization_id: str, incident_id: str, file_id: str) -> IncidentEvidence:
        evidence = self.repository.evidence.get((organization_id, incident_id, file_id)) or self._get_metadata(organization_id, incident_id, file_id)
        if evidence is None:
            raise KeyError("evidence not found")
        if evidence.deleted_at is not None:
            raise KeyError("evidence not found")
        return evidence

    def _retention_days_for(self, policy: EvidenceRetentionPolicy, evidence: IncidentEvidence) -> int:
        if evidence.kind == EvidenceKind.CLIP:
            return policy.clip_days
        if evidence.kind == EvidenceKind.METADATA:
            return policy.metadata_days
        return policy.snapshot_days

    def set_retention_policy(self, organization_id: str, metadata_days: int | None = None, snapshot_days: int | None = None, clip_days: int | None = None, audit_log_days: int | None = None, actor_user_id: str | None = None, reason: str | None = None) -> EvidenceRetentionPolicy:
        policy = self.repository.retention_policies.get(organization_id) or EvidenceRetentionPolicy(organization_id=organization_id)
        if metadata_days is not None:
            policy.metadata_days = metadata_days
        if snapshot_days is not None:
            policy.snapshot_days = snapshot_days
        if clip_days is not None:
            policy.clip_days = clip_days
        if audit_log_days is not None:
            policy.audit_log_days = audit_log_days
        policy.updated_at = datetime.now(timezone.utc)
        self.repository.retention_policies[organization_id] = policy
        if actor_user_id:
            self._audit(organization_id, actor_user_id, "retention.update", "-", "-", reason=reason, metadata_days=metadata_days, snapshot_days=snapshot_days, clip_days=clip_days, audit_log_days=audit_log_days)
            log_event("evidence.retention.update", organization_id=organization_id, actor_user_id=actor_user_id, reason=reason, metadata_days=metadata_days, snapshot_days=snapshot_days, clip_days=clip_days, audit_log_days=audit_log_days)
        return policy

    def get_retention_policy(self, organization_id: str) -> EvidenceRetentionPolicy:
        return self.repository.retention_policies.get(organization_id) or EvidenceRetentionPolicy(organization_id=organization_id)

    def register_evidence(self, organization_id: str, incident_id: str, file_id: str, media_type: str, size: int, uploaded_by: str, source: EvidenceSource, kind: EvidenceKind = EvidenceKind.SNAPSHOT, metadata: dict | None = None, object_key: str | None = None) -> IncidentEvidence:
        evidence = IncidentEvidence(organization_id=organization_id, incident_id=incident_id, file_id=file_id, object_key=object_key or self._object_key(organization_id, incident_id, file_id), media_type=media_type, size=size, source=source, uploaded_by=uploaded_by, kind=kind, metadata=dict(metadata or {}))
        self.repository.evidence[(organization_id, incident_id, file_id)] = evidence
        self._save_metadata(evidence)
        return evidence

    def request_upload_url(self, organization_id: str, incident_id: str, file_id: str, actor_user_id: str, source: EvidenceSource = EvidenceSource.USER, ttl_seconds: int | None = None) -> dict[str, object]:
        self.validate_bucket_privacy()
        evidence = self.register_evidence(organization_id, incident_id, file_id, "application/octet-stream", 0, actor_user_id, source, metadata={"pending": True})
        ttl = ttl_seconds or self.repository.default_ttl_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self._audit(organization_id, actor_user_id, "evidence.upload_url", incident_id, file_id, source=source.value, bucket=self.repository.bucket_name)
        log_event("evidence.upload_url", organization_id=organization_id, incident_id=incident_id, actor_user_id=actor_user_id, source=source.value, file_id=file_id)
        upload_url = self.storage.presign_upload(evidence.object_key, evidence.media_type, ttl)
        return {"object_key": evidence.object_key, "bucket": self.repository.bucket_name, "upload_url": upload_url, "expires_at": expires_at.isoformat()}

    def get_download_url(self, organization_id: str, incident_id: str, file_id: str, actor_user_id: str, permission_checked: bool = True, ttl_seconds: int | None = None) -> dict[str, object]:
        self.validate_bucket_privacy()
        if not permission_checked:
            raise PermissionError("permission required")
        evidence = self._find_evidence(organization_id, incident_id, file_id)
        ttl = ttl_seconds or self.repository.default_ttl_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self._audit(organization_id, actor_user_id, "evidence.download", incident_id, file_id, object_key=evidence.object_key, media_type=evidence.media_type)
        log_event("evidence.download", organization_id=organization_id, incident_id=incident_id, actor_user_id=actor_user_id, file_id=file_id, object_key=evidence.object_key)
        download_url = self.storage.presign_download(evidence.object_key, ttl)
        return {"bucket": self.repository.bucket_name, "object_key": evidence.object_key, "download_url": download_url, "expires_at": expires_at.isoformat()}

    def preview_expired_evidence(self, organization_id: str, now: datetime | None = None) -> list[dict[str, object]]:
        now = now or datetime.now(timezone.utc)
        policy = self.get_retention_policy(organization_id)
        preview: list[dict[str, object]] = []
        items = list(self.repository.evidence.items())
        list_by_org = getattr(self.metadata_repository, "list_by_organization", None)
        if callable(list_by_org):
            org_items = cast(list[IncidentEvidence], list_by_org(organization_id))
            items = [((e.organization_id, e.incident_id, e.file_id), e) for e in org_items]
        for (org_id, incident_id, file_id), evidence in items:
            if org_id != organization_id or evidence.deleted_at is not None:
                continue
            retention_days = self._retention_days_for(policy, evidence)
            expires_at = evidence.created_at + timedelta(days=retention_days)
            if expires_at <= now:
                preview.append({"organization_id": org_id, "incident_id": incident_id, "file_id": file_id, "object_key": evidence.object_key, "media_type": evidence.media_type, "expired_at": expires_at.isoformat()})
        self.repository.audit_logs.append(EvidenceAccessAuditLog(id=generate_token(12), organization_id=organization_id, actor_user_id="system", action="purge.dry_run", incident_id="-", file_id="-", created_at=now, metadata={"count": len(preview)}))
        log_event("evidence.purge.dry_run", organization_id=organization_id, actor_user_id="system", count=len(preview))
        return preview

    def list_evidence(self, organization_id: str, incident_id: str | None = None, limit: int | None = 50, offset: int = 0) -> list[IncidentEvidence]:
        items = list(self.repository.evidence.values())
        if hasattr(self.metadata_repository, "list_by_organization"):
            items = list(getattr(self.metadata_repository, "list_by_organization")(organization_id))
        items = [item for item in items if item.organization_id == organization_id and (incident_id is None or item.incident_id == incident_id)]
        return items[offset:] if limit is None else items[offset: offset + limit]

    def list_audit_logs(self, organization_id: str, incident_id: str | None = None, file_id: str | None = None, action: str | None = None, limit: int | None = 50, offset: int = 0) -> list[EvidenceAccessAuditLog]:
        logs = list(self.repository.audit_logs)
        list_all_audit_logs = getattr(self.metadata_repository, "list_audit_logs", None)
        if callable(list_all_audit_logs):
            logs = list(cast(list[EvidenceAccessAuditLog], list_all_audit_logs(organization_id)))
        if hasattr(self.metadata_repository, "audit_logs"):
            if incident_id is not None:
                logs = list(getattr(self.metadata_repository, "audit_logs")(organization_id, incident_id))
        logs = [log for log in logs if log.organization_id == organization_id and (incident_id is None or log.incident_id == incident_id) and (file_id is None or log.file_id == file_id) and (action is None or log.action == action)]
        return logs[offset:] if limit is None else logs[offset: offset + limit]

    def purge_expired_evidence(self, organization_id: str, confirm: bool = False, actor_user_id: str | None = None, reason: str | None = None, now: datetime | None = None) -> dict[str, object]:
        now = now or datetime.now(timezone.utc)
        expired = self.preview_expired_evidence(organization_id, now=now)
        if not confirm:
            raise EvidencePurgeError("purge requires explicit confirmation")
        purged: list[str] = []
        purged_items: list[dict[str, str]] = []
        for item in expired:
            key = (organization_id, str(item["incident_id"]), str(item["file_id"]))
            evidence = self.repository.evidence.get(key) or self._get_metadata(organization_id, str(item["incident_id"]), str(item["file_id"]))
            if evidence is None or evidence.deleted_at is not None:
                continue
            evidence.deleted_at = now
            mark_deleted = getattr(self.metadata_repository, "mark_deleted", None)
            if callable(mark_deleted):
                mark_deleted(organization_id, str(item["incident_id"]), str(item["file_id"]), deleted_at=now)
            delete = getattr(self.storage, "delete_object", None)
            if callable(delete):
                delete(evidence.object_key)
            purged.append(evidence.object_key)
            purged_items.append({"incident_id": evidence.incident_id, "file_id": evidence.file_id, "object_key": evidence.object_key})
        actor = actor_user_id or "system"
        if purged_items:
            for item in purged_items:
                self._audit(organization_id, actor, "purge.confirm", item["incident_id"], item["file_id"], reason=reason, object_key=item["object_key"], count=len(purged))
        else:
            self._audit(organization_id, actor, "purge.confirm", "-", "-", reason=reason, count=0)
        log_event("evidence.purge.confirm", organization_id=organization_id, actor_user_id=actor, reason=reason, count=len(purged))
        return {"organization_id": organization_id, "purged": purged, "count": len(purged)}

    def worker_can_request_upload(self, worker_organization_id: str, target_organization_id: str) -> bool:
        if worker_organization_id != target_organization_id:
            raise PermissionError("worker organization mismatch")
        return True
