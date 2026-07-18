from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select

from ..domain.operations import Camera, Department, EntityStatus, OperationInUse, RequiredPPE, SafetyRule, Site, Worker, Zone, ZoneType
from .models import Camera as CameraRow
from .models import Incident as IncidentRow
from .models import Department as DepartmentRow
from .models import RequiredPPE as RequiredPPERow
from .models import SafetyRule as SafetyRuleRow
from .models import Site as SiteRow
from .models import Worker as WorkerRow
from .models import Zone as ZoneRow


class SqlAlchemyOperationsRepository:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _ensure_aware(self, value: datetime | None) -> datetime:
        if value is None:
            return self._now()
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _save(self, row) -> None:
        with self.session_factory() as session:
            session.merge(row)
            session.commit()

    def _load_one(self, row_cls, key: str):
        with self.session_factory() as session:
            return session.get(row_cls, key)

    def _assert_org(self, organization_id: str, entity_org: str) -> None:
        if organization_id != entity_org:
            raise KeyError("cross-tenant relation denied")

    def _to_status(self, status: str | EntityStatus) -> str:
        return getattr(status, "value", status)

    def _to_domain_status(self, status: str) -> EntityStatus:
        return EntityStatus(status)

    def _site_domain(self, row: SiteRow | None) -> Site | None:
        if row is None:
            return None
        return Site(id=row.id, organization_id=row.organization_id, name=row.name, address=row.address, status=EntityStatus(row.status), created_at=self._ensure_aware(row.created_at), updated_at=self._ensure_aware(row.updated_at))

    def _dept_domain(self, row: DepartmentRow | None) -> Department | None:
        if row is None:
            return None
        return Department(id=row.id, organization_id=row.organization_id, site_id=row.site_id, name=row.name, status=EntityStatus(row.status), created_at=self._ensure_aware(row.created_at), updated_at=self._ensure_aware(row.updated_at))

    def _worker_domain(self, row: WorkerRow | None) -> Worker | None:
        if row is None:
            return None
        return Worker(id=row.id, organization_id=row.organization_id, name=row.name, internal_id=row.internal_id, site_id=row.site_id, department_id=row.department_id, status=EntityStatus(row.status), contact=row.contact, created_at=self._ensure_aware(row.created_at), updated_at=self._ensure_aware(row.updated_at))

    def _camera_domain(self, row: CameraRow | None) -> Camera | None:
        if row is None:
            return None
        return Camera(id=row.id, organization_id=row.organization_id, site_id=row.site_id, name=row.name, stream_identifier=row.stream_identifier, status=EntityStatus(row.status), metadata=json.loads(row.metadata_json or "{}"), created_at=self._ensure_aware(row.created_at), updated_at=self._ensure_aware(row.updated_at))

    def _zone_domain(self, row: ZoneRow | None) -> Zone | None:
        if row is None:
            return None
        return Zone(id=row.id, organization_id=row.organization_id, site_id=row.site_id, camera_id=row.camera_id, zone_type=ZoneType(row.zone_type), name=row.name, polygon_json=json.loads(row.polygon_json or "{}"), status=EntityStatus(row.status), created_at=self._ensure_aware(row.created_at), updated_at=self._ensure_aware(row.updated_at))

    def _rule_domain(self, row: SafetyRuleRow | None) -> SafetyRule | None:
        if row is None:
            return None
        return SafetyRule(id=row.id, organization_id=row.organization_id, site_id=row.site_id, zone_id=row.zone_id, name=row.name, status=EntityStatus(row.status), metadata=json.loads(row.metadata_json or "{}"), created_at=self._ensure_aware(row.created_at), updated_at=self._ensure_aware(row.updated_at))

    def _ppe_domain(self, row: RequiredPPERow | None) -> RequiredPPE | None:
        if row is None:
            return None
        return RequiredPPE(id=row.id, organization_id=row.organization_id, rule_id=row.rule_id, site_id=row.site_id, zone_id=row.zone_id, item=row.item, status=EntityStatus(row.status), created_at=self._ensure_aware(row.created_at), updated_at=self._ensure_aware(row.updated_at))

    def create_site(self, organization_id: str, name: str, address: str | None = None, status: EntityStatus = EntityStatus.ACTIVE, site_id: str | None = None) -> Site:
        site = Site(id=site_id or f"site-{name.lower().replace(' ', '-')}-{len(self.list_sites(organization_id))+1}", organization_id=organization_id, name=name, address=address, status=status)
        self._save(SiteRow(id=site.id, organization_id=site.organization_id, name=site.name, address=site.address, status=site.status.value, created_at=site.created_at, updated_at=site.updated_at))
        return site

    def update_site(self, organization_id: str, site_id: str, name: str | None = None, address: str | None = None, status: EntityStatus | None = None) -> Site:
        site = self._site_domain(self._load_one(SiteRow, site_id))
        if site is None:
            raise KeyError(site_id)
        self._assert_org(organization_id, site.organization_id)
        if name is not None:
            site.name = name
        if address is not None:
            site.address = address
        if status is not None:
            site.status = status
        site.updated_at = self._now()
        self._save(SiteRow(id=site.id, organization_id=site.organization_id, name=site.name, address=site.address, status=site.status.value, created_at=site.created_at, updated_at=site.updated_at))
        return site

    def list_sites(self, organization_id: str) -> list[Site]:
        if self.session_factory is None:
            return []
        with self.session_factory() as session:
            items: list[Site] = []
            for row in session.execute(select(SiteRow).where(SiteRow.organization_id == organization_id)).scalars().all():
                item = self._site_domain(row)
                if item is not None:
                    items.append(item)
            return items

    def create_department(self, organization_id: str, site_id: str, name: str, status: EntityStatus = EntityStatus.ACTIVE, department_id: str | None = None) -> Department:
        site = self._site_domain(self._load_one(SiteRow, site_id))
        if site is None:
            raise KeyError(site_id)
        self._assert_org(organization_id, site.organization_id)
        dept = Department(id=department_id or f"dept-{name.lower().replace(' ', '-')}-{len(self.list_departments(organization_id))+1}", organization_id=organization_id, site_id=site_id, name=name, status=status)
        self._save(DepartmentRow(id=dept.id, organization_id=dept.organization_id, site_id=dept.site_id, name=dept.name, status=dept.status.value, created_at=dept.created_at, updated_at=dept.updated_at))
        return dept

    def list_departments(self, organization_id: str) -> list[Department]:
        if self.session_factory is None:
            return []
        with self.session_factory() as session:
            items: list[Department] = []
            for row in session.execute(select(DepartmentRow).where(DepartmentRow.organization_id == organization_id)).scalars().all():
                item = self._dept_domain(row)
                if item is not None:
                    items.append(item)
            return items

    def create_worker(self, organization_id: str, name: str, internal_id: str, site_id: str | None = None, department_id: str | None = None, contact: str | None = None, status: EntityStatus = EntityStatus.ACTIVE, worker_id: str | None = None) -> Worker:
        if site_id is not None:
            site = self._site_domain(self._load_one(SiteRow, site_id))
            if site is None:
                raise KeyError(site_id)
            self._assert_org(organization_id, site.organization_id)
        if department_id is not None:
            dept = self._dept_domain(self._load_one(DepartmentRow, department_id))
            if dept is None:
                raise KeyError(department_id)
            self._assert_org(organization_id, dept.organization_id)
            if site_id is not None and dept.site_id != site_id:
                raise ValueError("department must belong to site")
        worker = Worker(id=worker_id or f"worker-{internal_id.lower()}", organization_id=organization_id, name=name, internal_id=internal_id, site_id=site_id, department_id=department_id, contact=contact, status=status)
        self._save(WorkerRow(id=worker.id, organization_id=worker.organization_id, name=worker.name, internal_id=worker.internal_id, site_id=worker.site_id, department_id=worker.department_id, status=worker.status.value, contact=worker.contact, created_at=worker.created_at, updated_at=worker.updated_at))
        return worker

    def list_workers(self, organization_id: str) -> list[Worker]:
        if self.session_factory is None:
            return []
        with self.session_factory() as session:
            items: list[Worker] = []
            for row in session.execute(select(WorkerRow).where(WorkerRow.organization_id == organization_id)).scalars().all():
                item = self._worker_domain(row)
                if item is not None:
                    items.append(item)
            return items

    def create_camera(self, organization_id: str, site_id: str, name: str, stream_identifier: str, status: EntityStatus = EntityStatus.ACTIVE, metadata: dict | None = None, camera_id: str | None = None) -> Camera:
        site = self._site_domain(self._load_one(SiteRow, site_id))
        if site is None:
            raise KeyError(site_id)
        self._assert_org(organization_id, site.organization_id)
        camera = Camera(id=camera_id or f"camera-{name.lower().replace(' ', '-')}-{len(self.list_cameras(organization_id))+1}", organization_id=organization_id, site_id=site_id, name=name, stream_identifier=stream_identifier, status=status, metadata=dict(metadata or {}))
        self._save(CameraRow(id=camera.id, organization_id=camera.organization_id, site_id=camera.site_id, name=camera.name, stream_identifier=camera.stream_identifier, status=camera.status.value, metadata_json=json.dumps(camera.metadata), created_at=camera.created_at, updated_at=camera.updated_at))
        return camera

    def update_camera(self, organization_id: str, camera_id: str, site_id: str | None = None, name: str | None = None, stream_identifier: str | None = None, status: EntityStatus | None = None, metadata: dict | None = None) -> Camera:
        camera = self._camera_domain(self._load_one(CameraRow, camera_id))
        if camera is None:
            raise KeyError(camera_id)
        self._assert_org(organization_id, camera.organization_id)
        if site_id is not None:
            site = self._site_domain(self._load_one(SiteRow, site_id))
            if site is None:
                raise KeyError(site_id)
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
        self._save(CameraRow(id=camera.id, organization_id=camera.organization_id, site_id=camera.site_id, name=camera.name, stream_identifier=camera.stream_identifier, status=camera.status.value, metadata_json=json.dumps(camera.metadata), created_at=camera.created_at, updated_at=camera.updated_at))
        return camera

    def list_cameras(self, organization_id: str) -> list[Camera]:
        if self.session_factory is None:
            return []
        with self.session_factory() as session:
            items: list[Camera] = []
            for row in session.execute(select(CameraRow).where(CameraRow.organization_id == organization_id)).scalars().all():
                item = self._camera_domain(row)
                if item is not None:
                    items.append(item)
            return items

    def create_zone(self, organization_id: str, site_id: str, camera_id: str, zone_type: ZoneType, polygon_json: dict, status: EntityStatus = EntityStatus.ACTIVE, zone_id: str | None = None, name: str | None = None) -> Zone:
        site = self._site_domain(self._load_one(SiteRow, site_id))
        camera = self._camera_domain(self._load_one(CameraRow, camera_id))
        if site is None or camera is None:
            raise KeyError("site/camera not found")
        self._assert_org(organization_id, site.organization_id)
        self._assert_org(organization_id, camera.organization_id)
        if camera.site_id != site_id:
            raise ValueError("camera must belong to site")
        zone = Zone(id=zone_id or f"zone-{zone_type.value}-{len(self.list_zones(organization_id))+1}", organization_id=organization_id, site_id=site_id, camera_id=camera_id, zone_type=zone_type, polygon_json=polygon_json, status=status, name=name)
        self._save(ZoneRow(id=zone.id, organization_id=zone.organization_id, site_id=zone.site_id, camera_id=zone.camera_id, zone_type=zone.zone_type.value, name=zone.name, polygon_json=json.dumps(zone.polygon_json), status=zone.status.value, created_at=zone.created_at, updated_at=zone.updated_at))
        return zone

    def update_zone(self, organization_id: str, zone_id: str, site_id: str | None = None, camera_id: str | None = None, zone_type: ZoneType | None = None, polygon_json: dict | None = None, status: EntityStatus | None = None, name: str | None = None) -> Zone:
        zone = self._zone_domain(self._load_one(ZoneRow, zone_id))
        if zone is None:
            raise KeyError(zone_id)
        self._assert_org(organization_id, zone.organization_id)
        if site_id is not None:
            site = self._site_domain(self._load_one(SiteRow, site_id))
            if site is None:
                raise KeyError(site_id)
            self._assert_org(organization_id, site.organization_id)
            zone.site_id = site_id
        if camera_id is not None:
            camera = self._camera_domain(self._load_one(CameraRow, camera_id))
            if camera is None:
                raise KeyError(camera_id)
            self._assert_org(organization_id, camera.organization_id)
            if camera.site_id != (site_id or zone.site_id):
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
        self._save(ZoneRow(id=zone.id, organization_id=zone.organization_id, site_id=zone.site_id, camera_id=zone.camera_id, zone_type=zone.zone_type.value, name=zone.name, polygon_json=json.dumps(zone.polygon_json), status=zone.status.value, created_at=zone.created_at, updated_at=zone.updated_at))
        return zone

    def list_zones(self, organization_id: str) -> list[Zone]:
        if self.session_factory is None:
            return []
        with self.session_factory() as session:
            items: list[Zone] = []
            for row in session.execute(select(ZoneRow).where(ZoneRow.organization_id == organization_id)).scalars().all():
                item = self._zone_domain(row)
                if item is not None:
                    items.append(item)
            return items

    def create_safety_rule(self, organization_id: str, name: str, site_id: str | None = None, zone_id: str | None = None, metadata: dict | None = None, status: EntityStatus = EntityStatus.ACTIVE, rule_id: str | None = None) -> SafetyRule:
        if site_id is not None:
            site = self._site_domain(self._load_one(SiteRow, site_id))
            if site is None:
                raise KeyError(site_id)
            self._assert_org(organization_id, site.organization_id)
        if zone_id is not None:
            zone = self._zone_domain(self._load_one(ZoneRow, zone_id))
            if zone is None:
                raise KeyError(zone_id)
            self._assert_org(organization_id, zone.organization_id)
        rule = SafetyRule(id=rule_id or f"rule-{name.lower().replace(' ', '-')}-{len(self.list_safety_rules(organization_id))+1}", organization_id=organization_id, site_id=site_id, zone_id=zone_id, name=name, metadata=dict(metadata or {}), status=status)
        self._save(SafetyRuleRow(id=rule.id, organization_id=rule.organization_id, site_id=rule.site_id, zone_id=rule.zone_id, name=rule.name, status=rule.status.value, metadata_json=json.dumps(rule.metadata), created_at=rule.created_at, updated_at=rule.updated_at))
        return rule

    def list_safety_rules(self, organization_id: str) -> list[SafetyRule]:
        if self.session_factory is None:
            return []
        with self.session_factory() as session:
            items: list[SafetyRule] = []
            for row in session.execute(select(SafetyRuleRow).where(SafetyRuleRow.organization_id == organization_id)).scalars().all():
                item = self._rule_domain(row)
                if item is not None:
                    items.append(item)
            return items

    def create_required_ppe(self, organization_id: str, rule_id: str, item: str, site_id: str | None = None, zone_id: str | None = None, status: EntityStatus = EntityStatus.ACTIVE, ppe_id: str | None = None) -> RequiredPPE:
        rule = self._rule_domain(self._load_one(SafetyRuleRow, rule_id))
        if rule is None:
            raise KeyError(rule_id)
        self._assert_org(organization_id, rule.organization_id)
        if site_id is not None:
            site = self._site_domain(self._load_one(SiteRow, site_id))
            if site is None:
                raise KeyError(site_id)
            self._assert_org(organization_id, site.organization_id)
        if zone_id is not None:
            zone = self._zone_domain(self._load_one(ZoneRow, zone_id))
            if zone is None:
                raise KeyError(zone_id)
            self._assert_org(organization_id, zone.organization_id)
        ppe = RequiredPPE(id=ppe_id or f"ppe-{item.lower().replace(' ', '-')}-{len(self.list_required_ppe(organization_id))+1}", organization_id=organization_id, rule_id=rule_id, site_id=site_id, zone_id=zone_id, item=item, status=status)
        self._save(RequiredPPERow(id=ppe.id, organization_id=ppe.organization_id, rule_id=ppe.rule_id, site_id=ppe.site_id, zone_id=ppe.zone_id, item=ppe.item, status=ppe.status.value, created_at=ppe.created_at, updated_at=ppe.updated_at))
        return ppe

    def list_required_ppe(self, organization_id: str) -> list[RequiredPPE]:
        if self.session_factory is None:
            return []
        with self.session_factory() as session:
            items: list[RequiredPPE] = []
            for row in session.execute(select(RequiredPPERow).where(RequiredPPERow.organization_id == organization_id)).scalars().all():
                item = self._ppe_domain(row)
                if item is not None:
                    items.append(item)
            return items

    def _incident_count(self, column, value: str) -> int:
        if select is None:
            return 0
        with self.session_factory() as session:
            return int(session.execute(select(func.count()).select_from(IncidentRow).where(column == value)).scalar() or 0)

    def delete_zone(self, organization_id: str, zone_id: str) -> None:
        """Zona com incidente no histórico não é apagada: o incidente guarda `zone_id`
        como texto (sem FK), então apagar deixaria a auditoria apontando para o nada.
        Nesse caso o caminho é desativar (`status`), que preserva a prova."""
        zone = self._zone_domain(self._load_one(ZoneRow, zone_id))
        if zone is None:
            raise KeyError(zone_id)
        self._assert_org(organization_id, zone.organization_id)
        if self._incident_count(IncidentRow.zone_id, zone_id) > 0:
            raise OperationInUse("zone has incidents")
        with self.session_factory() as session:
            row = session.get(ZoneRow, zone_id)
            if row is not None:
                session.delete(row)
                session.commit()

    def delete_camera(self, organization_id: str, camera_id: str) -> None:
        """Idem câmera. Cuidado extra: a FK de `zones.camera_id` é CASCADE, então apagar
        a câmera levaria as zonas junto — mais um motivo para barrar quando há histórico."""
        camera = self._camera_domain(self._load_one(CameraRow, camera_id))
        if camera is None:
            raise KeyError(camera_id)
        self._assert_org(organization_id, camera.organization_id)
        if self._incident_count(IncidentRow.camera_id, camera_id) > 0:
            raise OperationInUse("camera has incidents")
        with self.session_factory() as session:
            row = session.get(CameraRow, camera_id)
            if row is not None:
                session.delete(row)
                session.commit()

    def delete_site(self, organization_id: str, site_id: str) -> None:
        """Unidade só sai vazia: a FK é CASCADE e apagar levaria câmeras e zonas junto,
        silenciosamente."""
        site = self._site_domain(self._load_one(SiteRow, site_id))
        if site is None:
            raise KeyError(site_id)
        self._assert_org(organization_id, site.organization_id)
        if any(camera.site_id == site_id for camera in self.list_cameras(organization_id)):
            raise OperationInUse("site has cameras")
        with self.session_factory() as session:
            row = session.get(SiteRow, site_id)
            if row is not None:
                session.delete(row)
                session.commit()
