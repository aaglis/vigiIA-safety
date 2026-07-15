from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..domain.evidence import EvidenceKind, EvidenceSource
from ..domain.incidents import Incident, IncidentStatus, parse_detection_event
from ..persistence import models  # noqa: F401
from ..persistence.base import Base
from ..persistence.repositories import SqlAlchemyEvidenceRepository, SqlAlchemyIncidentRepository
from ..services.evidence import EvidenceService
from ..services.evidence_storage import MockEvidenceStorage

ORG_ID = "org-demo"
SITES = ["site-demo", "site-beta", "site-yard"]
CAMERAS = ["camera-demo-01", "camera-demo-02", "camera-demo-03", "camera-demo-04"]
ZONES = ["zone-demo-01", "zone-beta-02", "zone-yard-03"]
SEVERITIES = ["low", "medium", "high", "critical"]
STATUSES = [IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED, IncidentStatus.RESOLVED, IncidentStatus.DISMISSED]


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _measure(label: str, fn) -> dict[str, Any]:
    started = perf_counter()
    result = fn()
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    size = len(result) if hasattr(result, "__len__") else None
    return {"label": label, "elapsed_ms": elapsed_ms, "items": size}


def seed_synthetic_incidents_postgres(session_factory, count: int = 1000, *, organization_id: str = ORG_ID, days: int = 30, with_evidence_every: int = 25) -> tuple[SqlAlchemyIncidentRepository, EvidenceService, list[Incident]]:
    repo = SqlAlchemyIncidentRepository(session_factory)
    evidence_service = EvidenceService(storage=MockEvidenceStorage(bucket_name="vigia-evidence-private"), metadata_repository=SqlAlchemyEvidenceRepository(session_factory))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    incidents: list[Incident] = []
    for index in range(count):
        created_at = now - timedelta(minutes=index * max(1, days * 24 * 60 // max(1, count)))
        site_id = SITES[index % len(SITES)]
        camera_id = CAMERAS[index % len(CAMERAS)]
        zone_id = ZONES[index % len(ZONES)]
        incident = repo.create_from_detection(parse_detection_event({"organization_id": organization_id, "event_id": f"synthetic-event-{index:05d}", "site_id": site_id, "camera_id": camera_id, "zone_id": zone_id, "worker_id": f"worker-synthetic-{index % 3}", "event_type": "synthetic_detection", "severity": SEVERITIES[index % len(SEVERITIES)], "timestamp": _iso(created_at), "confidence": round(0.55 + (index % 40) / 100, 2), "model_version": "synthetic-baseline-v1", "summary": f"Incidente sintético {index:05d}", "metadata": {"synthetic": True, "bucket": index % 10}}))
        target_status = STATUSES[index % len(STATUSES)]
        if target_status == IncidentStatus.ACKNOWLEDGED:
            repo.transition(organization_id, incident.id, IncidentStatus.ACKNOWLEDGED, "synthetic-runner")
        elif target_status == IncidentStatus.RESOLVED:
            repo.transition(organization_id, incident.id, IncidentStatus.ACKNOWLEDGED, "synthetic-runner")
            repo.transition(organization_id, incident.id, IncidentStatus.RESOLVED, "synthetic-runner", reason="baseline synthetic resolution")
        elif target_status == IncidentStatus.DISMISSED:
            repo.transition(organization_id, incident.id, IncidentStatus.DISMISSED, "synthetic-runner", reason="baseline synthetic dismissal")
        stored = repo.get(organization_id, incident.id)
        if stored is not None:
            incidents.append(stored)
        if with_evidence_every > 0 and index % with_evidence_every == 0:
            evidence_service.register_evidence(organization_id, incident.id, f"synthetic-file-{index:05d}", "application/json", 256, "synthetic-runner", EvidenceSource.EDGE_WORKER, EvidenceKind.METADATA, {"synthetic": True, "camera_id": camera_id, "zone_id": zone_id, "site_id": site_id})
    return repo, evidence_service, incidents


def run_baseline_postgres(database_url: str, count: int = 1000, *, organization_id: str = ORG_ID, days: int = 30) -> dict[str, Any]:
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    repo, evidence_service, incidents = seed_synthetic_incidents_postgres(Session, count=count, organization_id=organization_id, days=days)
    selected = incidents[count // 2]
    recent_from = datetime.now(timezone.utc) - timedelta(days=7)
    first_evidence_incident = next((item.id for item in incidents if evidence_service.list_evidence(organization_id, incident_id=item.id)), selected.id)
    measurements = [
        _measure("list_first_page", lambda: repo.list_filtered(organization_id)[:50]),
        _measure("filter_status_open", lambda: repo.list_filtered(organization_id, status="open")[:50]),
        _measure("filter_severity_high", lambda: repo.list_filtered(organization_id, severity="high")[:50]),
        _measure("filter_site_camera_zone", lambda: repo.list_filtered(organization_id, site_id=selected.site_id, camera_id=selected.camera_id, zone_id=selected.zone_id)[:50]),
        _measure("filter_recent_7_days", lambda: repo.list_filtered(organization_id, created_from=recent_from)[:50]),
        _measure("detail_lookup", lambda: [repo.get(organization_id, selected.id)]),
        _measure("audit_lookup", lambda: repo.audit_logs(organization_id, selected.id)),
        _measure("evidence_lookup", lambda: evidence_service.list_evidence(organization_id, incident_id=first_evidence_incident)),
    ]
    return {"kind": "incident_volume_baseline_postgres", "organization_id": organization_id, "count": count, "days": days, "postgres": True, "measurements": measurements, "recommendation": "Use at least 1k synthetic incidents to compare dashboard query latency against the in-memory baseline; if filters slow down materially, add/verify indexes for organization_id+created_at, organization_id+status+severity, and the most common site/camera/zone combo."}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed and measure synthetic incident volume against PostgreSQL without sensitive data.")
    parser.add_argument("--database-url", default="")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--organization-id", default=ORG_ID)
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("--database-url is required")
    if args.count < 1:
        raise SystemExit("--count must be >= 1")
    print(json.dumps(run_baseline_postgres(args.database_url, count=args.count, organization_id=args.organization_id, days=args.days), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
