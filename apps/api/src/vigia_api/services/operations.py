from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..domain.operations import (
    Camera,
    Department,
    EntityStatus,
    OperationInUse,
    OperationalAuditLog,
    RequiredPPE,
    SafetyRule,
    Site,
    Worker,
    Zone,
    ZoneType,
)


class InMemoryOperationsRepository:
    """Espelha a interface do repositório SQL. `incident_lookup` responde se há
    histórico apontando para uma câmera/zona — em memória não há tabela de incidentes,
    então quem monta o container injeta a checagem."""

    def __init__(self) -> None:
        self._incident_lookup: Any | None = None
        self.sites: dict[str, Site] = {}
        self.departments: dict[str, Department] = {}
        self.workers: dict[str, Worker] = {}
        self.cameras: dict[str, Camera] = {}
        self.zones: dict[str, Zone] = {}
        self.safety_rules: dict[str, SafetyRule] = {}
        self.required_ppe: dict[str, RequiredPPE] = {}
        self.audit_logs: list[OperationalAuditLog] = []

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _assert_org(self, organization_id: str, entity_org: str) -> None:
        if organization_id != entity_org:
            raise KeyError("cross-tenant relation denied")

    def _record(self, organization_id: str | None, actor_user_id: str, action: str, target_type: str, target_id: str, ip: str | None = None, **metadata: object) -> None:
        self.audit_logs.append(OperationalAuditLog(id=f"audit-{len(self.audit_logs)+1}", organization_id=organization_id, actor_user_id=actor_user_id, action=action, target_type=target_type, target_id=target_id, ip=ip, metadata_json=metadata, created_at=self._now()))

    def create_site(self, organization_id: str, name: str, address: str | None = None, status: EntityStatus = EntityStatus.ACTIVE, site_id: str | None = None) -> Site:
        site = Site(id=site_id or f"site-{len(self.sites)+1}", organization_id=organization_id, name=name, address=address, status=status)
        self.sites[site.id] = site
        return site

    def update_site(self, organization_id: str, site_id: str, name: str | None = None, address: str | None = None, status: EntityStatus | None = None) -> Site:
        site = self.sites[site_id]
        self._assert_org(organization_id, site.organization_id)
        if name is not None:
            site.name = name
        if address is not None:
            site.address = address
        if status is not None:
            site.status = status
        site.updated_at = self._now()
        return site

    def create_department(self, organization_id: str, site_id: str, name: str, status: EntityStatus = EntityStatus.ACTIVE, department_id: str | None = None) -> Department:
        site = self.sites[site_id]
        self._assert_org(organization_id, site.organization_id)
        dept = Department(id=department_id or f"dept-{len(self.departments)+1}", organization_id=organization_id, site_id=site_id, name=name, status=status)
        self.departments[dept.id] = dept
        return dept

    def create_worker(self, organization_id: str, name: str, internal_id: str, site_id: str | None = None, department_id: str | None = None, contact: str | None = None, status: EntityStatus = EntityStatus.ACTIVE, worker_id: str | None = None) -> Worker:
        if site_id is not None:
            site = self.sites[site_id]
            self._assert_org(organization_id, site.organization_id)
        if department_id is not None:
            dept = self.departments[department_id]
            self._assert_org(organization_id, dept.organization_id)
            if site_id is not None and dept.site_id != site_id:
                raise ValueError("department must belong to site")
        worker = Worker(id=worker_id or f"worker-{len(self.workers)+1}", organization_id=organization_id, name=name, internal_id=internal_id, site_id=site_id, department_id=department_id, contact=contact, status=status)
        self.workers[worker.id] = worker
        return worker

    def create_camera(self, organization_id: str, site_id: str, name: str, stream_identifier: str, status: EntityStatus = EntityStatus.ACTIVE, metadata: dict | None = None, camera_id: str | None = None) -> Camera:
        site = self.sites[site_id]
        self._assert_org(organization_id, site.organization_id)
        camera = Camera(id=camera_id or f"camera-{len(self.cameras)+1}", organization_id=organization_id, site_id=site_id, name=name, stream_identifier=stream_identifier, status=status, metadata=dict(metadata or {}))
        self.cameras[camera.id] = camera
        return camera

    def update_camera(self, organization_id: str, camera_id: str, site_id: str | None = None, name: str | None = None, stream_identifier: str | None = None, status: EntityStatus | None = None, metadata: dict | None = None) -> Camera:
        camera = self.cameras[camera_id]
        self._assert_org(organization_id, camera.organization_id)
        if site_id is not None:
            site = self.sites[site_id]
            self._assert_org(organization_id, site.organization_id)
            camera.site_id = site_id
        if name is not None:
            camera.name = name
        if stream_identifier is not None:
            camera.stream_identifier = stream_identifier
        if status is not None:
            camera.status = status
        if metadata is not None:
            camera.metadata = dict(metadata)
        camera.updated_at = self._now()
        return camera

    def create_zone(self, organization_id: str, site_id: str, camera_id: str, zone_type: ZoneType, polygon_json: dict, status: EntityStatus = EntityStatus.ACTIVE, zone_id: str | None = None, name: str | None = None) -> Zone:
        site = self.sites[site_id]
        camera = self.cameras[camera_id]
        self._assert_org(organization_id, site.organization_id)
        self._assert_org(organization_id, camera.organization_id)
        if camera.site_id != site_id:
            raise ValueError("camera must belong to site")
        zone = Zone(id=zone_id or f"zone-{len(self.zones)+1}", organization_id=organization_id, site_id=site_id, camera_id=camera_id, zone_type=zone_type, polygon_json=polygon_json, status=status, name=name)
        self.zones[zone.id] = zone
        return zone

    def update_zone(self, organization_id: str, zone_id: str, site_id: str | None = None, camera_id: str | None = None, zone_type: ZoneType | None = None, polygon_json: dict | None = None, status: EntityStatus | None = None, name: str | None = None) -> Zone:
        zone = self.zones[zone_id]
        self._assert_org(organization_id, zone.organization_id)
        if site_id is not None:
            site = self.sites[site_id]
            self._assert_org(organization_id, site.organization_id)
            zone.site_id = site_id
        if camera_id is not None:
            camera = self.cameras[camera_id]
            self._assert_org(organization_id, camera.organization_id)
            if site_id is not None and camera.site_id != site_id:
                raise ValueError("camera must belong to site")
            if site_id is None and camera.site_id != zone.site_id:
                raise ValueError("camera must belong to site")
            zone.camera_id = camera_id
        if zone_type is not None:
            zone.zone_type = zone_type
        if polygon_json is not None:
            zone.polygon_json = dict(polygon_json)
        if status is not None:
            zone.status = status
        if name is not None:
            zone.name = name.strip() or None
        zone.updated_at = self._now()
        return zone

    def create_safety_rule(self, organization_id: str, name: str, site_id: str | None = None, zone_id: str | None = None, metadata: dict | None = None, status: EntityStatus = EntityStatus.ACTIVE, rule_id: str | None = None) -> SafetyRule:
        if site_id is not None:
            self._assert_org(organization_id, self.sites[site_id].organization_id)
        if zone_id is not None:
            self._assert_org(organization_id, self.zones[zone_id].organization_id)
        rule = SafetyRule(id=rule_id or f"rule-{len(self.safety_rules)+1}", organization_id=organization_id, site_id=site_id, zone_id=zone_id, name=name, metadata=dict(metadata or {}), status=status)
        self.safety_rules[rule.id] = rule
        return rule

    def create_required_ppe(self, organization_id: str, rule_id: str, item: str, site_id: str | None = None, zone_id: str | None = None, status: EntityStatus = EntityStatus.ACTIVE, ppe_id: str | None = None) -> RequiredPPE:
        rule = self.safety_rules[rule_id]
        self._assert_org(organization_id, rule.organization_id)
        if site_id is not None:
            self._assert_org(organization_id, self.sites[site_id].organization_id)
        if zone_id is not None:
            self._assert_org(organization_id, self.zones[zone_id].organization_id)
        ppe = RequiredPPE(id=ppe_id or f"ppe-{len(self.required_ppe)+1}", organization_id=organization_id, rule_id=rule_id, site_id=site_id, zone_id=zone_id, item=item, status=status)
        self.required_ppe[ppe.id] = ppe
        return ppe

    def ensure_camera_scope(self, organization_id: str, site_id: str, camera_id: str) -> Camera:
        camera = self.cameras[camera_id]
        if camera.organization_id != organization_id or camera.site_id != site_id:
            raise KeyError("camera out of scope")
        return camera

    def ensure_worker_scope(self, organization_id: str, site_id: str, worker_id: str) -> Worker:
        worker = self.workers[worker_id]
        if worker.organization_id != organization_id or worker.site_id != site_id:
            raise KeyError("worker out of scope")
        return worker

    def list_sites(self, organization_id: str) -> list[Site]:
        return [site for site in self.sites.values() if site.organization_id == organization_id]

    def list_departments(self, organization_id: str) -> list[Department]:
        return [dept for dept in self.departments.values() if dept.organization_id == organization_id]

    def list_workers(self, organization_id: str) -> list[Worker]:
        return [worker for worker in self.workers.values() if worker.organization_id == organization_id]

    def list_cameras(self, organization_id: str) -> list[Camera]:
        return [camera for camera in self.cameras.values() if camera.organization_id == organization_id]

    def list_zones(self, organization_id: str) -> list[Zone]:
        return [zone for zone in self.zones.values() if zone.organization_id == organization_id]

    def list_safety_rules(self, organization_id: str) -> list[SafetyRule]:
        return [rule for rule in self.safety_rules.values() if rule.organization_id == organization_id]

    def list_required_ppe(self, organization_id: str) -> list[RequiredPPE]:
        return [ppe for ppe in self.required_ppe.values() if ppe.organization_id == organization_id]

    def delete_zone(self, organization_id: str, zone_id: str) -> None:
        zone = self.zones.get(zone_id)
        if zone is None or zone.organization_id != organization_id:
            raise KeyError(zone_id)
        if self._incident_lookup and self._incident_lookup("zone", zone_id):
            raise OperationInUse("zone has incidents")
        self.zones.pop(zone_id, None)

    def delete_camera(self, organization_id: str, camera_id: str) -> None:
        camera = self.cameras.get(camera_id)
        if camera is None or camera.organization_id != organization_id:
            raise KeyError(camera_id)
        if self._incident_lookup and self._incident_lookup("camera", camera_id):
            raise OperationInUse("camera has incidents")
        # Espelha o CASCADE do banco: zona sem câmera não faz sentido.
        for zid in [z.id for z in self.zones.values() if z.camera_id == camera_id]:
            self.zones.pop(zid, None)
        self.cameras.pop(camera_id, None)

    def delete_site(self, organization_id: str, site_id: str) -> None:
        site = self.sites.get(site_id)
        if site is None or site.organization_id != organization_id:
            raise KeyError(site_id)
        if any(c.site_id == site_id for c in self.cameras.values()):
            raise OperationInUse("site has cameras")
        self.sites.pop(site_id, None)
