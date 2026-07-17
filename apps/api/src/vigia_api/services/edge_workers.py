from __future__ import annotations

from time import perf_counter
from datetime import datetime, timezone
from typing import Any, Protocol, cast

from ..domain.edge_workers import EdgeWorker, EdgeWorkerStatus
from ..domain.evidence import EvidenceSource
from ..domain.incidents import parse_detection_event
from .evidence import EvidenceService
from .incidents import InMemoryIncidentRepository, incident_to_dict
from .security import generate_token, hash_token
from ..observability import increment_metric, log_event


class InMemoryEdgeWorkerRepository:
    def __init__(self) -> None:
        self.workers: dict[str, EdgeWorker] = {}
        self.workers_by_client_id: dict[str, str] = {}
        self.camera_catalog: dict[tuple[str, str], set[str]] = {}

    def save(self, worker: EdgeWorker) -> None:
        self.workers[worker.id] = worker
        self.workers_by_client_id[worker.client_id] = worker.id

    def get(self, worker_id: str) -> EdgeWorker | None:
        return self.workers.get(worker_id)

    def get_by_client_id(self, client_id: str) -> EdgeWorker | None:
        worker_id = self.workers_by_client_id.get(client_id)
        return self.workers.get(worker_id) if worker_id else None

    def list_by_organization(self, organization_id: str) -> list[EdgeWorker]:
        return [worker for worker in self.workers.values() if worker.organization_id == organization_id]

    def list_all(self) -> list[EdgeWorker]:
        return list(self.workers.values())

    def delete(self, worker_id: str) -> None:
        worker = self.workers.pop(worker_id, None)
        if worker is not None:
            self.workers_by_client_id.pop(worker.client_id, None)

    def update_last_heartbeat(self, worker_id: str, last_heartbeat_at: datetime) -> None:
        worker = self.workers[worker_id]
        worker.last_heartbeat_at = last_heartbeat_at
        worker.updated_at = last_heartbeat_at

    def update_status(self, worker_id: str, status: EdgeWorkerStatus) -> None:
        worker = self.workers[worker_id]
        worker.status = status
        worker.updated_at = datetime.now(timezone.utc)


class EdgeWorkerRepositoryProtocol(Protocol):
    def save(self, worker: EdgeWorker) -> None: ...
    def get(self, worker_id: str) -> EdgeWorker | None: ...
    def get_by_client_id(self, client_id: str) -> EdgeWorker | None: ...
    def list_all(self) -> list[EdgeWorker]: ...
    def update_last_heartbeat(self, worker_id: str, last_heartbeat_at: datetime) -> None: ...
    def update_status(self, worker_id: str, status: EdgeWorkerStatus) -> None: ...


class EdgeWorkerService:
    def __init__(self, incident_repository: Any | None = None, repository: EdgeWorkerRepositoryProtocol | None = None, evidence_service: EvidenceService | None = None, operations_repository: Any | None = None) -> None:
        self.repository: Any = repository or InMemoryEdgeWorkerRepository()
        self.incident_repository = incident_repository or InMemoryIncidentRepository()
        self.evidence_service = evidence_service
        self.operations_repository = operations_repository
        self.camera_catalog = getattr(cast(Any, self.repository), "camera_catalog", {})

    def _serialize_worker(self, worker: EdgeWorker) -> dict[str, Any]:
        return {
            "id": worker.id,
            "organization_id": worker.organization_id,
            "site_id": worker.site_id,
            "name": worker.name,
            "client_id": worker.client_id,
            "allowed_camera_ids": list(worker.allowed_camera_ids),
            "status": worker.status.value,
            "last_heartbeat_at": worker.last_heartbeat_at.isoformat() if worker.last_heartbeat_at else None,
            "created_at": worker.created_at.isoformat(),
            "updated_at": worker.updated_at.isoformat(),
        }

    def register_worker(self, organization_id: str, site_id: str, name: str, allowed_camera_ids: list[str]) -> tuple[EdgeWorker, str]:
        worker_id = generate_token(12)
        client_id = generate_token(16)
        api_key = generate_token(32)
        worker = EdgeWorker(
            id=worker_id,
            organization_id=organization_id,
            site_id=site_id,
            name=name,
            client_id=client_id,
            api_key_hash=hash_token(api_key),
            allowed_camera_ids=list(allowed_camera_ids),
        )
        self.repository.save(worker)
        self.camera_catalog[(organization_id, site_id)] = set(allowed_camera_ids)
        return worker, api_key

    def _authenticate(self, client_id: str, api_key: str) -> EdgeWorker:
        worker = self.repository.get_by_client_id(client_id)
        if not worker:
            log_event("edge_worker.auth.failure", level="warning", client_id=client_id)
            raise PermissionError("invalid worker credentials")
        if worker.status != EdgeWorkerStatus.ACTIVE or worker.api_key_hash != hash_token(api_key):
            log_event("edge_worker.auth.failure", level="warning", organization_id=worker.organization_id, edge_worker_id=worker.id)
            increment_metric("detections", ("rejected", "auth"))
            raise PermissionError("worker revoked or invalid")
        return worker

    def config(self, client_id: str, api_key: str) -> dict[str, object]:
        worker = self._authenticate(client_id, api_key)
        ops = self.operations_repository
        zones = []
        safety_rules = []
        required_ppe = []
        cameras = []
        if ops is not None:
            cameras = [
                {"id": c.id, "site_id": c.site_id, "name": c.name, "stream_identifier": c.stream_identifier, "status": c.status.value, "metadata": c.metadata}
                for c in ops.list_cameras(worker.organization_id)
                if c.id in worker.allowed_camera_ids
            ]
            zones = [
                {"id": z.id, "site_id": z.site_id, "camera_id": z.camera_id, "zone_type": z.zone_type.value, "name": z.name, "status": z.status.value, "polygon_json": z.polygon_json}
                for z in ops.list_zones(worker.organization_id)
                if z.site_id == worker.site_id
            ]
            zone_ids = {z["id"] for z in zones}
            safety_rules = []
            for r in ops.list_safety_rules(worker.organization_id):
                is_global = r.site_id is None and r.zone_id is None
                site_matches = r.site_id == worker.site_id
                zone_matches = r.zone_id is not None and r.zone_id in zone_ids
                if is_global or site_matches or zone_matches:
                    safety_rules.append({"id": r.id, "site_id": r.site_id, "zone_id": r.zone_id, "name": r.name, "status": r.status.value, "metadata": r.metadata})
            required_ppe = []
            for p in ops.list_required_ppe(worker.organization_id):
                is_global = p.site_id is None and p.zone_id is None
                site_matches = p.site_id == worker.site_id
                zone_matches = p.zone_id is not None and p.zone_id in zone_ids
                if is_global or site_matches or zone_matches:
                    required_ppe.append({"id": p.id, "rule_id": p.rule_id, "site_id": p.site_id, "zone_id": p.zone_id, "item": p.item, "status": p.status.value})
        return {
            "worker": self._serialize_worker(worker),
            "capabilities": ["heartbeat", "publish_detection", "request_evidence_upload"],
            "allowed_camera_ids": worker.allowed_camera_ids,
            "cameras": cameras,
            "site_id": worker.site_id,
            "zones": zones,
            "safety_rules": safety_rules,
            "required_ppe": required_ppe,
        }

    def heartbeat(self, client_id: str, api_key: str) -> EdgeWorker:
        worker = self._authenticate(client_id, api_key)
        now = datetime.now(timezone.utc)
        worker.last_heartbeat_at = now
        worker.updated_at = now
        self.repository.update_last_heartbeat(worker.id, now)
        increment_metric("edge_heartbeat", (worker.organization_id, "ok"))
        log_event("edge_worker.heartbeat", organization_id=worker.organization_id, edge_worker_id=worker.id, client_id=worker.client_id)
        return worker

    def request_evidence_upload(self, client_id: str, api_key: str, file_id: str, incident_id: str | None = None) -> dict[str, str]:
        worker = self._authenticate(client_id, api_key)
        if incident_id:
            path = f"org/{worker.organization_id}/incidents/{incident_id}/evidence/{file_id}"
        else:
            path = f"org/{worker.organization_id}/edge-workers/{worker.id}/evidence/{file_id}"
        log_event("edge_worker.evidence_upload_requested", organization_id=worker.organization_id, edge_worker_id=worker.id, incident_id=incident_id, file_id=file_id)
        result: dict[str, str] = {"upload_path": path}
        storage = getattr(self.evidence_service, "storage", None)
        if storage is not None:
            try:
                repository = getattr(self.evidence_service, "repository", None)
                result["upload_url"] = storage.presign_upload(path, "application/octet-stream", getattr(repository, "default_ttl_seconds", 300))
            except Exception:
                pass
        return result

    def revoke(self, worker_id: str) -> EdgeWorker:
        worker = self.repository.get(worker_id)
        if worker is None:
            raise KeyError(worker_id)
        worker.status = EdgeWorkerStatus.REVOKED
        worker.updated_at = datetime.now(timezone.utc)
        self.repository.update_status(worker_id, EdgeWorkerStatus.REVOKED)
        log_event("edge_worker.revoked", organization_id=worker.organization_id, edge_worker_id=worker.id)
        return worker

    def submit_detection(self, client_id: str, api_key: str, payload: dict[str, object]) -> dict[str, object]:
        started = perf_counter()
        worker = self._authenticate(client_id, api_key)
        if payload.get("organization_id") not in {None, worker.organization_id}:
            log_event("edge_worker.detection_rejected", organization_id=worker.organization_id, edge_worker_id=worker.id, reason="organization mismatch")
            increment_metric("detections", ("rejected", "organization"))
            raise PermissionError("organization mismatch")
        if payload.get("site_id") not in {None, worker.site_id}:
            log_event("edge_worker.detection_rejected", organization_id=worker.organization_id, edge_worker_id=worker.id, reason="site mismatch")
            increment_metric("detections", ("rejected", "site"))
            raise PermissionError("site mismatch")
        camera_id = str(payload["camera_id"])
        if camera_id not in worker.allowed_camera_ids:
            log_event("edge_worker.detection_rejected", organization_id=worker.organization_id, edge_worker_id=worker.id, reason="camera not allowed")
            increment_metric("detections", ("rejected", "camera"))
            raise PermissionError("camera not allowed")
        camera_catalog = self.camera_catalog.get((worker.organization_id, worker.site_id), set())
        if camera_id not in camera_catalog:
            log_event("edge_worker.detection_rejected", organization_id=worker.organization_id, edge_worker_id=worker.id, reason="camera not registered for site")
            increment_metric("detections", ("rejected", "camera_catalog"))
            raise PermissionError("camera not registered for site")
        event = parse_detection_event({
            **payload,
            "organization_id": worker.organization_id,
            "camera_id": camera_id,
        })
        incident = self.incident_repository.create_from_detection(event)
        evidence = cast(dict[str, Any], payload["evidence"]) if isinstance(payload.get("evidence"), dict) else None
        if evidence and self.evidence_service is not None:
            file_id = str(evidence.get("file_id") or event.event_id)
            metadata = cast(dict[str, Any], payload.get("metadata") or {})
            upload_path = str(evidence.get("upload_path")) if evidence.get("upload_path") else None
            self.evidence_service.register_evidence(worker.organization_id, incident.id, file_id, "application/octet-stream", int(evidence.get("size") or 0), worker.id, source=EvidenceSource.EDGE_WORKER, object_key=upload_path, metadata={"file_id": file_id, "upload_path": upload_path, "upload_status": evidence.get("upload_status"), "upload_error": evidence.get("upload_error"), "sha256_hex": evidence.get("sha256_hex"), "frame_timestamp": evidence.get("frame_timestamp"), "source_type": evidence.get("source_type"), "cv_mode": metadata.get("cv_mode")})
        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        log_event("edge_worker.detection_accepted", organization_id=worker.organization_id, incident_id=incident.id, edge_worker_id=worker.id, detection_to_incident_ms=elapsed_ms)
        increment_metric("detections", ("accepted", worker.organization_id))
        increment_metric("incidents", (incident.status.value, worker.organization_id))
        return {"incident": incident_to_dict(incident), "worker_id": worker.id}

    def is_offline(self, worker_id: str, threshold_seconds: int = 300, now: datetime | None = None) -> bool:
        worker = self.repository.get(worker_id)
        if worker is None:
            raise KeyError(worker_id)
        now = now or datetime.now(timezone.utc)
        if worker.last_heartbeat_at is None:
            increment_metric("worker_offline", (worker.organization_id, "offline"))
            return True
        offline = (now - worker.last_heartbeat_at).total_seconds() > threshold_seconds
        if offline:
            increment_metric("worker_offline", (worker.organization_id, "offline"))
        return offline

    def list_offline_workers(self, threshold_seconds: int = 300, now: datetime | None = None) -> list[EdgeWorker]:
        if hasattr(self.repository, "list_all"):
            return [worker for worker in self.repository.list_all() if self.is_offline(worker.id, threshold_seconds=threshold_seconds, now=now)]
        workers = getattr(self.repository, "workers", {})
        return [worker for worker in workers.values() if self.is_offline(worker.id, threshold_seconds=threshold_seconds, now=now)]
