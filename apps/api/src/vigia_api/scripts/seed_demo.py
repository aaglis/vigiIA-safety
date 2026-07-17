from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from ..container import AppContainer, build_container, default_container
from ..domain.auth import MembershipSummary, OrganizationSummary, Permission, PlatformRole
from ..domain.edge_workers import EdgeWorker
from ..domain.incidents import IncidentStatus, parse_detection_event
from ..domain.operations import ZoneType
from ..services.auth import InMemoryAuthRepository
from ..services.incidents import InMemoryIncidentRepository
from ..services.security import hash_password, hash_token
from ..settings import settings

PLATFORM_ADMIN_EMAIL = "platform@vigia.local"
PLATFORM_ADMIN_PASSWORD = "change-me-dev"
PLATFORM_ADMIN_ID = "user-platform-admin"
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
# Cada câmera demo aponta para uma câmera RTSP do stack de câmeras de dev
# (infra/compose/docker-compose.cameras.yml), onde cada vídeo da pasta vira `cam-<arquivo>`.
# Em produção, estas URLs são as câmeras IP do cliente.
DEMO_CAMERA_STREAM = os.environ.get("DEMO_CAMERA_STREAM", "rtsp://cameras:8554/cam-sample-ppe")
DEMO_CAMERA_STREAM_PATIO = os.environ.get("DEMO_CAMERA_STREAM_PATIO", "rtsp://cameras:8554/cam-pexels-262484")
DEMO_CAMERA_STREAM_DOCA = os.environ.get("DEMO_CAMERA_STREAM_DOCA", "rtsp://cameras:8554/cam-pixabay-13439512")


BASE_SITES: list[dict[str, str]] = [
    {"id": DEMO_SITE_ID, "name": "Planta Demo", "address": "Av. Demo, 100"},
    {"id": "site-demo-patio-sul", "name": "Pátio Sul", "address": "Rodovia Industrial, Km 12"},
    {"id": "site-demo-doca-norte", "name": "Doca Norte", "address": "Rua do Porto, 900"},
]

BASE_CAMERAS: list[dict[str, Any]] = [
    {
        "id": DEMO_CAMERA_ID,
        "site_id": DEMO_SITE_ID,
        "name": "Camera Demo 01",
        "stream_identifier": DEMO_CAMERA_STREAM,
        "metadata": {"purpose": "primary-demo", "video_fixture_url": "/demo-media/camera-demo-01.mp4", "video_fixture_path": "fixtures/demo/camera-demo-01.mp4", "cv_scenarios": ["missing_helmet", "restricted_access"], "expected_events": ["helmet_missing", "restricted_zone_entry"], "location_label": "Planta Demo / Portaria"},
    },
    {
        "id": "camera-demo-patio-sul-01",
        "site_id": "site-demo-patio-sul",
        "name": "Pátio Sul - Entrada de Caminhões",
        "stream_identifier": DEMO_CAMERA_STREAM_PATIO,
        "metadata": {"purpose": "vehicle_gating", "video_fixture_url": "/demo-media/patio-sul-entrada-caminhoes.mp4", "video_fixture_path": "fixtures/demo/patio-sul-entrada-caminhoes.mp4", "cv_scenarios": ["vehicle_pedestrian_access", "missing_reflective_vest"], "expected_events": ["vehicle_entry", "high_visibility_missing"], "location_label": "Pátio Sul / Portaria 2"},
    },
    {
        "id": "camera-demo-doca-norte-01",
        "site_id": "site-demo-doca-norte",
        "name": "Doca Norte - Linha de Separação",
        "stream_identifier": DEMO_CAMERA_STREAM_DOCA,
        "metadata": {"purpose": "ppe_validation", "video_fixture_url": "/demo-media/doca-norte-linha-2-pintura.mp4", "video_fixture_path": "fixtures/demo/doca-norte-linha-2-pintura.mp4", "cv_scenarios": ["missing_goggles", "missing_gloves"], "expected_events": ["ppe_violation", "paint_line_entry"], "location_label": "Doca Norte / Linha 2 Pintura"},
    },
]

# polygon em coordenadas normalizadas [0..1] do frame — usado pela geometria do worker.
BASE_ZONES: list[dict[str, Any]] = [
    {"id": DEMO_ZONE_ID, "site_id": DEMO_SITE_ID, "camera_id": DEMO_CAMERA_ID, "zone_type": ZoneType.RESTRICTED, "name": "Área Restrita Demo", "polygon": {"type": "polygon", "points": [[0.15, 0.4], [0.85, 0.4], [0.85, 0.95], [0.15, 0.95]]}},
    {"id": "zone-demo-01-ppe", "site_id": DEMO_SITE_ID, "camera_id": DEMO_CAMERA_ID, "zone_type": ZoneType.PPE, "name": "EPI Obrigatório Demo", "polygon": {"type": "polygon", "points": [[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]]}},
    {"id": "zone-demo-patio-sul-access", "site_id": "site-demo-patio-sul", "camera_id": "camera-demo-patio-sul-01", "zone_type": ZoneType.ACCESS, "name": "Portaria 2 / Acesso de Veículos", "polygon": {}},
    {"id": "zone-demo-doca-norte-ppe", "site_id": "site-demo-doca-norte", "camera_id": "camera-demo-doca-norte-01", "zone_type": ZoneType.PPE, "name": "Linha 2 Pintura / EPI Obrigatório", "polygon": {}},
]

BASE_WORKERS: list[dict[str, str]] = [
    {"id": DEMO_WORKER_ID, "name": "Operador Demo", "internal_id": "W-001", "site_id": DEMO_SITE_ID},
    {"id": "worker-demo-02", "name": "Visitante Controlado", "internal_id": "V-014", "site_id": "site-demo-patio-sul"},
]

BASE_SAFETY_RULES: list[dict[str, Any]] = [
    {"id": "rule-helmet-required-1", "name": "Capacete obrigatório", "site_id": DEMO_SITE_ID, "zone_id": DEMO_ZONE_ID, "metadata": {"priority": "high", "cv_scenarios": ["missing_helmet"], "safety_topic": "helmet"}, "ppe": [{"id": "ppe-helmet-demo", "item": "helmet"}]},
    {"id": "rule-reflective-vest-patio-sul", "name": "Colete refletivo obrigatório", "site_id": "site-demo-patio-sul", "zone_id": "zone-demo-patio-sul-access", "metadata": {"priority": "high", "cv_scenarios": ["missing_reflective_vest", "vehicle_pedestrian_access"], "safety_topic": "high_visibility"}, "ppe": [{"id": "ppe-vest-patio-sul", "item": "reflective vest"}]},
    {"id": "rule-goggles-gloves-doca-norte", "name": "Óculos e luvas obrigatórios", "site_id": "site-demo-doca-norte", "zone_id": "zone-demo-doca-norte-ppe", "metadata": {"priority": "medium", "cv_scenarios": ["missing_goggles", "missing_gloves"], "safety_topic": "paint_line"}, "ppe": [{"id": "ppe-goggles-doca-norte", "item": "safety goggles"}, {"id": "ppe-gloves-doca-norte", "item": "gloves"}]},
    {"id": "rule-restricted-access-maintenance", "name": "Acesso restrito à manutenção", "site_id": DEMO_SITE_ID, "zone_id": DEMO_ZONE_ID, "metadata": {"priority": "critical", "cv_scenarios": ["restricted_area_access"], "safety_topic": "access_control"}, "ppe": []},
]


auth_repository = InMemoryAuthRepository()
operations_repository = default_container.operations_repository


def _replace_key(mapping: dict[str, Any], old_id: str, new_id: str, value: Any) -> None:
    if old_id != new_id:
        mapping.pop(old_id, None)
    mapping[new_id] = value


def _ensure_auth_demo_memory(repository: InMemoryAuthRepository) -> dict[str, Any]:
    repository.seed_demo_user()
    org_user = repository.get_user_by_email(DEMO_USER_EMAIL)
    assert org_user is not None
    org_user.id = DEMO_USER_ID
    org_user.email = DEMO_USER_EMAIL
    org_user.full_name = "VigIA Org Admin"
    org_user.password_hash = hash_password(DEMO_USER_PASSWORD)
    org_user.platform_role = PlatformRole.NONE
    repository.add_user(org_user)
    platform_user = repository.get_user_by_email(PLATFORM_ADMIN_EMAIL)
    if platform_user is None:
        platform_user = repository.users.get(PLATFORM_ADMIN_ID)
    if platform_user is None:
        platform_user = repository.users.get(DEMO_USER_ID)
    if platform_user is None:
        platform_user = org_user
    platform_user = type(org_user)(id=PLATFORM_ADMIN_ID, email=PLATFORM_ADMIN_EMAIL, full_name="VigIA Platform Admin", password_hash=hash_password(PLATFORM_ADMIN_PASSWORD), platform_role=PlatformRole.PLATFORM_ADMIN, is_active=True, email_verified_at=org_user.email_verified_at, created_at=org_user.created_at)
    repository.add_user(platform_user)
    repository.memberships[platform_user.id] = [MembershipSummary(organization=OrganizationSummary(id=DEMO_ORGANIZATION_ID, name="VigIA Local", slug=DEMO_ORGANIZATION_SLUG), role="platform_admin", permissions=[Permission.VIEW_DASHBOARD, Permission.MANAGE_USERS, Permission.MANAGE_ORG], active=True)]
    org = OrganizationSummary(id=DEMO_ORGANIZATION_ID, name="VigIA Local", slug=DEMO_ORGANIZATION_SLUG)
    membership = MembershipSummary(organization=org, role="org_owner", permissions=[Permission.VIEW_DASHBOARD, Permission.MANAGE_USERS, Permission.MANAGE_ORG], active=True)
    memberships = [item for item in repository.memberships.get(org_user.id, []) if item.organization.id not in {DEMO_ORGANIZATION_ID, "org-dev"}]
    repository.memberships[org_user.id] = [membership, *memberships]
    return {"user_id": org_user.id, "org_id": DEMO_ORGANIZATION_ID, "platform_user_id": platform_user.id}


def _ensure_auth_demo_postgres(container: AppContainer) -> dict[str, Any]:
    if container.session_factory is None:
        raise RuntimeError("postgres seed requires SQLAlchemy session factory")
    from sqlalchemy import select
    from ..persistence.models import Organization, OrganizationMembership, User

    now = datetime.now(timezone.utc)
    with container.session_factory() as session:
        org = session.get(Organization, DEMO_ORGANIZATION_ID)
        if org is None:
            session.add(Organization(id=DEMO_ORGANIZATION_ID, name="VigIA Local", legal_name="VigIA Local Demo", tax_id="DEMO-ORG-001", status="active", retention_days=365, created_at=now, updated_at=now))

        org_user = session.get(User, DEMO_USER_ID)
        if org_user is None:
            org_user = session.execute(select(User).where(User.email_normalized == DEMO_USER_EMAIL)).scalar_one_or_none()
        if org_user is None:
            org_user = User(id=DEMO_USER_ID, email=DEMO_USER_EMAIL, email_normalized=DEMO_USER_EMAIL, full_name="VigIA Org Admin", password_hash=hash_password(DEMO_USER_PASSWORD), platform_role="none", is_active=True, email_verified_at=now, created_at=now, updated_at=now)
            session.add(org_user)
        else:
            org_user.email = DEMO_USER_EMAIL
            org_user.email_normalized = DEMO_USER_EMAIL
            org_user.full_name = "VigIA Org Admin"
            org_user.password_hash = hash_password(DEMO_USER_PASSWORD)
            org_user.platform_role = "none"
            org_user.is_active = True
            org_user.email_verified_at = org_user.email_verified_at or now

        platform_user = session.get(User, PLATFORM_ADMIN_ID)
        if platform_user is None:
            platform_user = session.execute(select(User).where(User.email_normalized == PLATFORM_ADMIN_EMAIL)).scalar_one_or_none()
        if platform_user is None:
            platform_user = User(id=PLATFORM_ADMIN_ID, email=PLATFORM_ADMIN_EMAIL, email_normalized=PLATFORM_ADMIN_EMAIL, full_name="VigIA Platform Admin", password_hash=hash_password(PLATFORM_ADMIN_PASSWORD), platform_role="platform_admin", is_active=True, email_verified_at=now, created_at=now, updated_at=now)
            session.add(platform_user)
        else:
            platform_user.email = PLATFORM_ADMIN_EMAIL
            platform_user.email_normalized = PLATFORM_ADMIN_EMAIL
            platform_user.full_name = "VigIA Platform Admin"
            platform_user.password_hash = hash_password(PLATFORM_ADMIN_PASSWORD)
            platform_user.platform_role = "platform_admin"
            platform_user.is_active = True
            platform_user.email_verified_at = platform_user.email_verified_at or now
        session.flush()

        platform_membership = session.execute(select(OrganizationMembership).where(OrganizationMembership.organization_id == DEMO_ORGANIZATION_ID, OrganizationMembership.user_id == platform_user.id)).scalar_one_or_none()
        if platform_membership is None:
            session.add(OrganizationMembership(id="membership-demo-platform-admin", organization_id=DEMO_ORGANIZATION_ID, user_id=platform_user.id, role="platform_admin", status="active", invited_by=None, joined_at=now, created_at=now, updated_at=now))

        membership = session.execute(select(OrganizationMembership).where(OrganizationMembership.organization_id == DEMO_ORGANIZATION_ID, OrganizationMembership.user_id == org_user.id)).scalar_one_or_none()
        if membership is None:
            session.add(OrganizationMembership(id="membership-demo-owner", organization_id=DEMO_ORGANIZATION_ID, user_id=org_user.id, role="org_owner", status="active", invited_by=None, joined_at=now, created_at=now, updated_at=now))
        session.commit()
        return {"user_id": org_user.id, "org_id": DEMO_ORGANIZATION_ID, "platform_user_id": platform_user.id}


def _ensure_operations_demo(container: AppContainer, org_id: str) -> dict[str, str]:
    repo = container.operations_repository
    sites = {site.id: site for site in repo.list_sites(org_id)}
    for payload in BASE_SITES:
        if payload["id"] not in sites:
            sites[payload["id"]] = repo.create_site(org_id, name=payload["name"], address=payload["address"], site_id=payload["id"])

    cameras = {camera.id: camera for camera in repo.list_cameras(org_id)}
    for payload in BASE_CAMERAS:
        if payload["id"] not in cameras:
            cameras[payload["id"]] = repo.create_camera(org_id, payload["site_id"], name=payload["name"], stream_identifier=payload["stream_identifier"], metadata=payload["metadata"], camera_id=payload["id"])

    zones = {zone.id: zone for zone in repo.list_zones(org_id)}
    for payload in BASE_ZONES:
        if payload["id"] not in zones:
            zones[payload["id"]] = repo.create_zone(org_id, payload["site_id"], payload["camera_id"], zone_type=payload["zone_type"], polygon_json=payload.get("polygon") or {}, zone_id=payload["id"])

    workers = {worker.id: worker for worker in repo.list_workers(org_id)}
    for payload in BASE_WORKERS:
        if payload["id"] not in workers:
            workers[payload["id"]] = repo.create_worker(org_id, name=payload["name"], internal_id=payload["internal_id"], site_id=payload["site_id"], worker_id=payload["id"])

    rules = {rule.id: rule for rule in repo.list_safety_rules(org_id)}
    ppe_items = {ppe.id: ppe for ppe in repo.list_required_ppe(org_id)}
    for payload in BASE_SAFETY_RULES:
        rule = rules.get(payload["id"])
        if rule is None:
            rule = repo.create_safety_rule(org_id, payload["name"], site_id=payload["site_id"], zone_id=payload["zone_id"], metadata=payload["metadata"], rule_id=payload["id"])
            rules[rule.id] = rule
        for ppe_payload in payload["ppe"]:
            ppe_id = ppe_payload["id"]
            if ppe_id not in ppe_items:
                ppe_items[ppe_id] = repo.create_required_ppe(org_id, rule.id, ppe_payload["item"], site_id=payload["site_id"], zone_id=payload["zone_id"], ppe_id=ppe_id)

    return {"site_id": DEMO_SITE_ID, "camera_id": DEMO_CAMERA_ID, "zone_id": DEMO_ZONE_ID, "worker_id": DEMO_WORKER_ID}


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


def _ensure_incident_demo(container: AppContainer, org_id: str, camera_id: str, zone_id: str, worker_id: str) -> dict[str, Any]:
    repo = container.incident_repository
    existing = next((i for i in repo.list_by_organization(org_id) if i.detection_event_id == DEMO_DETECTION_EVENT_ID), None)
    if existing is None:
        incident = repo.create_from_detection(parse_detection_event({"organization_id": org_id, "event_id": DEMO_DETECTION_EVENT_ID, "camera_id": camera_id, "zone_id": zone_id, "worker_id": worker_id, "severity": "medium", "summary": "Demo incident"}))
        repo.transition(org_id, incident.id, IncidentStatus.ACKNOWLEDGED, "demo-admin")
        return {"incident_id": incident.id, "status": "acknowledged", "seeded": True}
    return {"incident_id": existing.id, "status": existing.status.value, "seeded": False}


def seed_demo(container: AppContainer | None = None, with_incident: bool = False) -> dict[str, Any]:
    container = container or (build_container(settings, seed_dev=False) if settings.repository_backend == "postgres" else default_container)
    auth = _ensure_auth_demo_postgres(container) if container.repository_backend == "postgres" else _ensure_auth_demo_memory(container.auth_repository)
    if container.repository_backend == "memory":
        _ensure_auth_demo_memory(auth_repository)
    ops = _ensure_operations_demo(container, auth["org_id"])
    edge = _ensure_edge_worker_demo(container, auth["org_id"], ops["site_id"], ops["camera_id"])
    incident = _ensure_incident_demo(container, auth["org_id"], ops["camera_id"], ops["zone_id"], ops["worker_id"]) if with_incident else {"incident_id": None, "status": None, "seeded": False}
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
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--with-incident", action="store_true")
    parser.add_argument("--with-incidents", action="store_true")
    args = parser.parse_args()
    summary = seed_demo(with_incident=bool(args.with_incident or args.with_incidents))
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
