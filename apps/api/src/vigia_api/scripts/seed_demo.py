from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..container import AppContainer, build_container, default_container
from ..domain.auth import MembershipSummary, OrganizationSummary, Permission
from ..domain.edge_workers import EdgeWorker
from ..domain.incidents import IncidentStatus, parse_detection_event
from ..domain.operations import ZoneType
from ..services.auth import InMemoryAuthRepository
from ..services.incidents import InMemoryIncidentRepository
from ..services.security import hash_password, hash_token
from ..settings import settings

DEMO_USER_EMAIL = "admin@vigia.local"
DEMO_USER_PASSWORD = "change-me-dev"
DEMO_USER_ID = "user-dev"
DEMO_ORGANIZATION_ID = "org-demo"
DEMO_ORGANIZATION_SLUG = "vigia-local"
DEMO_SITE_ID = "site-demo"
DEMO_CAMERA_ID = "camera-demo-01"
DEMO_ZONE_ID = "zone-demo-01"
DEMO_WORKER_ID = "worker-demo-01"
DEMO_EDGE_WORKER_ID = "edge-worker-demo"
DEMO_EDGE_CLIENT_ID = "dev-client-id"
DEMO_DETECTION_EVENT_ID = "demo-detection-01"


auth_repository = InMemoryAuthRepository()
operations_repository = default_container.operations_repository


def _replace_key(mapping: dict[str, Any], old_id: str, new_id: str, value: Any) -> None:
    if old_id != new_id:
        mapping.pop(old_id, None)
    mapping[new_id] = value


def _ensure_auth_demo_memory(repository: InMemoryAuthRepository) -> dict[str, str]:
    repository.seed_demo_user()
    user = repository.get_user_by_email(DEMO_USER_EMAIL)
    assert user is not None
    org = OrganizationSummary(id=DEMO_ORGANIZATION_ID, name="VigIA Local", slug=DEMO_ORGANIZATION_SLUG)
    membership = MembershipSummary(organization=org, role="org_owner", permissions=[Permission.VIEW_DASHBOARD, Permission.MANAGE_USERS, Permission.MANAGE_ORG], active=True)
    memberships = [item for item in repository.memberships.get(user.id, []) if item.organization.id not in {DEMO_ORGANIZATION_ID, "org-dev"}]
    repository.memberships[user.id] = [membership, *memberships]
    return {"user_id": user.id, "org_id": DEMO_ORGANIZATION_ID}


def _ensure_auth_demo_postgres(container: AppContainer) -> dict[str, str]:
    if container.session_factory is None:
        raise RuntimeError("postgres seed requires SQLAlchemy session factory")
    from sqlalchemy import select
    from ..persistence.models import Organization, OrganizationMembership, User

    now = datetime.now(timezone.utc)
    with container.session_factory() as session:
        org = session.get(Organization, DEMO_ORGANIZATION_ID)
        if org is None:
            session.add(Organization(id=DEMO_ORGANIZATION_ID, name="VigIA Local", legal_name="VigIA Local Demo", tax_id="DEMO-ORG-001", status="active", retention_days=365, created_at=now, updated_at=now))

        user = session.get(User, DEMO_USER_ID)
        if user is None:
            user = session.execute(select(User).where(User.email_normalized == DEMO_USER_EMAIL)).scalar_one_or_none()
        if user is None:
            user = User(id=DEMO_USER_ID, email=DEMO_USER_EMAIL, email_normalized=DEMO_USER_EMAIL, full_name="VigIA Admin", password_hash=hash_password(DEMO_USER_PASSWORD), platform_role="none", is_active=True, email_verified_at=now, created_at=now, updated_at=now)
            session.add(user)
        session.flush()

        membership = session.execute(select(OrganizationMembership).where(OrganizationMembership.organization_id == DEMO_ORGANIZATION_ID, OrganizationMembership.user_id == user.id)).scalar_one_or_none()
        if membership is None:
            session.add(OrganizationMembership(id="membership-demo-owner", organization_id=DEMO_ORGANIZATION_ID, user_id=user.id, role="org_owner", status="active", invited_by=None, joined_at=now, created_at=now, updated_at=now))
        session.commit()
        return {"user_id": user.id, "org_id": DEMO_ORGANIZATION_ID}


def _ensure_operations_demo(container: AppContainer, org_id: str) -> dict[str, str]:
    repo = container.operations_repository
    site = next((s for s in repo.list_sites(org_id) if s.id == DEMO_SITE_ID), None)
    if site is None:
        site = repo.create_site(org_id, name="Planta Demo", address="Av. Demo, 100", site_id=DEMO_SITE_ID)
    camera = next((c for c in repo.list_cameras(org_id) if c.id == DEMO_CAMERA_ID), None)
    if camera is None:
        camera = repo.create_camera(org_id, site.id, name="Camera Demo 01", stream_identifier="rtsp://demo/camera-01", camera_id=DEMO_CAMERA_ID)
    zone = next((z for z in repo.list_zones(org_id) if z.id == DEMO_ZONE_ID), None)
    if zone is None:
        zone = repo.create_zone(org_id, site.id, camera.id, zone_type=ZoneType.RESTRICTED, polygon_json={"type": "Polygon", "coordinates": []}, zone_id=DEMO_ZONE_ID)
    worker = next((w for w in repo.list_workers(org_id) if w.id == DEMO_WORKER_ID), None)
    if worker is None:
        worker = repo.create_worker(org_id, name="Operador Demo", internal_id="W-001", site_id=site.id, worker_id=DEMO_WORKER_ID)
    rule = next((r for r in repo.list_safety_rules(org_id) if r.id == "rule-helmet-required-1"), None)
    if rule is None:
        rule = repo.create_safety_rule(org_id, "Helmet required", site_id=site.id, zone_id=zone.id, metadata={"priority": "high"}, rule_id="rule-helmet-required-1")
    ppe = next((p for p in repo.list_required_ppe(org_id) if p.id == "ppe-helmet-1"), None)
    if ppe is None:
        ppe = repo.create_required_ppe(org_id, rule.id, "helmet", site_id=site.id, zone_id=zone.id, ppe_id="ppe-helmet-1")
    return {"site_id": site.id, "camera_id": camera.id, "zone_id": zone.id, "worker_id": worker.id}


def _ensure_edge_worker_demo(container: AppContainer, org_id: str, site_id: str, camera_id: str) -> dict[str, str]:
    service = container.edge_worker_service
    existing = service.repository.get_by_client_id(settings.edge_worker_client_id or DEMO_EDGE_CLIENT_ID) or service.repository.get(DEMO_EDGE_WORKER_ID)
    if existing is None:
        worker = EdgeWorker(id=DEMO_EDGE_WORKER_ID, organization_id=org_id, site_id=site_id, name="Edge Worker Demo", client_id=settings.edge_worker_client_id or DEMO_EDGE_CLIENT_ID, api_key_hash=hash_token(settings.edge_worker_api_key), allowed_camera_ids=[camera_id])
        service.repository.save(worker)
        service.camera_catalog[(org_id, site_id)] = {camera_id}
        return {"edge_worker_id": worker.id, "client_id": worker.client_id, "api_key_status": "configured"}
    service.camera_catalog[(existing.organization_id, existing.site_id)] = set(existing.allowed_camera_ids)
    return {"edge_worker_id": existing.id, "client_id": existing.client_id, "api_key_status": "existing"}


def _ensure_incident_demo(container: AppContainer, org_id: str, camera_id: str, zone_id: str, worker_id: str) -> dict[str, str]:
    repo = container.incident_repository
    existing = next((i for i in repo.list_by_organization(org_id) if i.detection_event_id == DEMO_DETECTION_EVENT_ID), None)
    if existing is None:
        incident = repo.create_from_detection(parse_detection_event({"organization_id": org_id, "event_id": DEMO_DETECTION_EVENT_ID, "camera_id": camera_id, "zone_id": zone_id, "worker_id": worker_id, "severity": "medium", "summary": "Demo incident"}))
        repo.transition(org_id, incident.id, IncidentStatus.ACKNOWLEDGED, "demo-admin")
        return {"incident_id": incident.id, "status": "acknowledged"}
    return {"incident_id": existing.id, "status": existing.status.value}


def seed_demo(container: AppContainer | None = None) -> dict[str, Any]:
    container = container or (build_container(settings, seed_dev=False) if settings.repository_backend == "postgres" else default_container)
    auth = _ensure_auth_demo_postgres(container) if container.repository_backend == "postgres" else _ensure_auth_demo_memory(container.auth_repository)
    if container.repository_backend == "memory":
        _ensure_auth_demo_memory(auth_repository)
    ops = _ensure_operations_demo(container, auth["org_id"])
    edge = _ensure_edge_worker_demo(container, auth["org_id"], ops["site_id"], ops["camera_id"])
    incident = _ensure_incident_demo(container, auth["org_id"], ops["camera_id"], ops["zone_id"], ops["worker_id"])
    incidents = container.incident_repository.list_by_organization(auth["org_id"])
    edge_workers = container.edge_worker_service.repository.list_by_organization(auth["org_id"])
    return {
        "backend": container.repository_backend,
        "user": auth,
        "organization": {"id": auth["org_id"], "slug": DEMO_ORGANIZATION_SLUG},
        "operations": ops,
        "edge_worker": edge,
        "incident": incident,
        "counts": {
            "users": len(auth_repository.users) if container.repository_backend == "memory" else 1,
            "organizations": 1,
            "sites": len(container.operations_repository.list_sites(auth["org_id"])),
            "cameras": len(container.operations_repository.list_cameras(auth["org_id"])),
            "zones": len(container.operations_repository.list_zones(auth["org_id"])),
            "workers": len(container.operations_repository.list_workers(auth["org_id"])),
            "edge_workers": len(edge_workers),
            "incidents": len(incidents),
        },
    }


def main() -> None:
    summary = seed_demo()
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
