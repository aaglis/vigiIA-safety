from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request

from pydantic import BaseModel, ConfigDict, Field

from ...container import default_container
from ...domain.auth import Permission
from ...domain.operations import EntityStatus, OperationInUse, ZoneType, classify_stream_source, validate_stream_identifier
from ...settings import settings
from ...security.csrf import require_csrf
from ...security.origin import validate_origin_or_referer
from ...security.dependencies import get_current_organization_membership, require_permission

router = APIRouter(tags=["operations"])
service = default_container.operations_repository


def _service(request: Request | None):
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.operations_repository if container is not None else service


def _assert_organization_access(organization_id: str, membership) -> None:
    if membership.organization.id != organization_id:
        raise HTTPException(status_code=403, detail="organization access denied")


class SiteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    address: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE


class CameraIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str
    name: str
    stream_identifier: str
    status: EntityStatus = EntityStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)


class CameraUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str
    name: str
    # Edição pelo navegador NÃO recebe a URL atual de volta. Ausente/null/"" mantém o
    # segredo já salvo; valor preenchido troca o stream e revalida por ambiente.
    stream_identifier: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE
    metadata: dict[str, Any] | None = None


class ZoneIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: str
    camera_id: str
    zone_type: ZoneType
    # Nome da área como ela é conhecida na planta ("Porta da Doca").
    name: str | None = Field(default=None, max_length=120)
    polygon_json: dict[str, Any] = Field(default_factory=dict)
    status: EntityStatus = EntityStatus.ACTIVE


def _serialize_site_entity(site) -> dict[str, Any]:
    return {"id": site.id, "organization_id": site.organization_id, "name": site.name, "address": site.address, "status": site.status.value}


def _display_stream_identifier(stream_identifier: str) -> str:
    """Valor seguro para o navegador: nunca inclui usuário, senha, host ou path.

    `stream_identifier` é segredo operacional (ex.: rtsp://user:pass@host/path). O edge
    worker recebe o valor bruto em `/edge-workers/me/config`, mas endpoints de Operações
    são consumidos por usuários humanos e só mostram o tipo da fonte.
    """
    source_type = classify_stream_source(stream_identifier) or urlsplit(stream_identifier).scheme.lower() or "stream"
    labels = {"rtsp": "RTSP configurado", "rtmp": "RTMP configurado", "http": "HTTP configurado", "video": "Vídeo de teste configurado"}
    label = labels.get(source_type, "Fonte configurada")
    parsed = urlsplit(stream_identifier)
    if parsed.username or parsed.password:
        return f"{label} · credenciais ocultas"
    return label


def _serialize_camera_entity(camera) -> dict[str, Any]:
    source_type = str((camera.metadata or {}).get("source_type") or classify_stream_source(camera.stream_identifier) or "stream")
    return {
        "id": camera.id,
        "organization_id": camera.organization_id,
        "site_id": camera.site_id,
        "name": camera.name,
        "display_stream_identifier": _display_stream_identifier(camera.stream_identifier),
        "stream_source_type": source_type,
        "status": camera.status.value,
        "metadata": camera.metadata,
    }


def _camera_metadata_with_source(stream_identifier: str, metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Valida o stream por ambiente (422 se inválido) e grava o source_type derivado no metadata."""
    try:
        source_type = validate_stream_identifier(stream_identifier, settings.app_env)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {**(metadata or {}), "source_type": source_type}


def _serialize_zone_entity(zone) -> dict[str, Any]:
    return {"id": zone.id, "organization_id": zone.organization_id, "site_id": zone.site_id, "camera_id": zone.camera_id, "zone_type": zone.zone_type.value, "name": zone.name, "polygon_json": zone.polygon_json, "status": zone.status.value}


def _key_error_status(exc: KeyError) -> int:
    return 403 if exc.args and exc.args[0] == "cross-tenant relation denied" else 404


def _serialize_site(site, cameras: list[dict[str, Any]], zones: list[dict[str, Any]], rules: list[dict[str, Any]], ppe: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": site.id,
        "organization_id": site.organization_id,
        "name": site.name,
        "address": site.address,
        "status": site.status.value,
        "cameras": cameras,
        "zones": zones,
        "safety_rules": rules,
        "required_ppe": ppe,
    }


def _serialize_catalog(operations_repo, organization_id: str) -> dict[str, Any]:
    sites = operations_repo.list_sites(organization_id)
    cameras = operations_repo.list_cameras(organization_id)
    zones = operations_repo.list_zones(organization_id)
    rules = operations_repo.list_safety_rules(organization_id)
    ppe = operations_repo.list_required_ppe(organization_id)

    cameras_by_site: dict[str, list[dict[str, Any]]] = {site.id: [] for site in sites}
    zones_by_site: dict[str, list[dict[str, Any]]] = {site.id: [] for site in sites}
    rules_by_site: dict[str, list[dict[str, Any]]] = {site.id: [] for site in sites}
    ppe_by_site: dict[str, list[dict[str, Any]]] = {site.id: [] for site in sites}

    serial_cameras = []
    for camera in cameras:
        payload = _serialize_camera_entity(camera)
        serial_cameras.append(payload)
        cameras_by_site.setdefault(camera.site_id, []).append(payload)

    serial_zones = []
    for zone in zones:
        # Mesmo serializer dos demais endpoints: montar o payload à mão aqui já fez o
        # catálogo esquecer `name` e `polygon_json`, e a tela mostrava o id cru.
        payload = _serialize_zone_entity(zone)
        serial_zones.append(payload)
        zones_by_site.setdefault(zone.site_id, []).append(payload)

    serial_rules = []
    for rule in rules:
        payload = {"id": rule.id, "organization_id": rule.organization_id, "site_id": rule.site_id, "zone_id": rule.zone_id, "name": rule.name, "status": rule.status.value, "metadata": rule.metadata}
        serial_rules.append(payload)
        if rule.site_id is not None:
            rules_by_site.setdefault(rule.site_id, []).append(payload)

    serial_ppe = []
    for item in ppe:
        payload = {"id": item.id, "organization_id": item.organization_id, "rule_id": item.rule_id, "site_id": item.site_id, "zone_id": item.zone_id, "item": item.item, "status": item.status.value}
        serial_ppe.append(payload)
        if item.site_id is not None:
            ppe_by_site.setdefault(item.site_id, []).append(payload)

    serial_sites = []
    for site in sites:
        serial_sites.append(_serialize_site(site, cameras_by_site.get(site.id, []), zones_by_site.get(site.id, []), rules_by_site.get(site.id, []), ppe_by_site.get(site.id, [])))

    return {"organization_id": organization_id, "sites": serial_sites, "cameras": serial_cameras, "zones": serial_zones, "safety_rules": serial_rules, "required_ppe": serial_ppe}


@router.get("/organizations/{organization_id}/operations/catalog", dependencies=[Depends(require_permission(Permission.VIEW_DASHBOARD))])
def get_catalog(organization_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    _assert_organization_access(organization_id, membership)
    return _serialize_catalog(_service(request), organization_id)


@router.post("/organizations/{organization_id}/operations/sites", dependencies=[Depends(require_permission("sites.manage")), Depends(require_csrf)])
def create_site(organization_id: str, payload: SiteIn, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    validate_origin_or_referer(request)
    _assert_organization_access(organization_id, membership)
    try:
        return {"site": _serialize_site_entity(_service(request).create_site(organization_id, payload.name, payload.address, payload.status))}
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail=str(exc)) from exc


@router.patch("/organizations/{organization_id}/operations/sites/{site_id}", dependencies=[Depends(require_permission("sites.manage")), Depends(require_csrf)])
def update_site(organization_id: str, site_id: str, payload: SiteIn, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    validate_origin_or_referer(request)
    _assert_organization_access(organization_id, membership)
    try:
        return {"site": _serialize_site_entity(_service(request).update_site(organization_id, site_id, payload.name, payload.address, payload.status))}
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail=str(exc)) from exc


@router.post("/organizations/{organization_id}/operations/cameras", dependencies=[Depends(require_permission("cameras.manage")), Depends(require_csrf)])
def create_camera(organization_id: str, payload: CameraIn, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    validate_origin_or_referer(request)
    _assert_organization_access(organization_id, membership)
    metadata = _camera_metadata_with_source(payload.stream_identifier, payload.metadata)
    try:
        return {"camera": _serialize_camera_entity(_service(request).create_camera(organization_id, payload.site_id, payload.name, payload.stream_identifier, payload.status, metadata))}
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.patch("/organizations/{organization_id}/operations/cameras/{camera_id}", dependencies=[Depends(require_permission("cameras.manage")), Depends(require_csrf)])
def update_camera(organization_id: str, camera_id: str, payload: CameraUpdateIn, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    validate_origin_or_referer(request)
    _assert_organization_access(organization_id, membership)
    stream_identifier = payload.stream_identifier.strip() if payload.stream_identifier else None
    metadata = _camera_metadata_with_source(stream_identifier, payload.metadata) if stream_identifier is not None else payload.metadata
    try:
        return {"camera": _serialize_camera_entity(_service(request).update_camera(organization_id, camera_id, payload.site_id, payload.name, stream_identifier, payload.status, metadata))}
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/organizations/{organization_id}/operations/zones", dependencies=[Depends(require_permission("zones.manage")), Depends(require_csrf)])
def create_zone(organization_id: str, payload: ZoneIn, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    validate_origin_or_referer(request)
    _assert_organization_access(organization_id, membership)
    try:
        return {"zone": _serialize_zone_entity(_service(request).create_zone(organization_id, payload.site_id, payload.camera_id, payload.zone_type, payload.polygon_json, payload.status, name=payload.name))}
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.patch("/organizations/{organization_id}/operations/zones/{zone_id}", dependencies=[Depends(require_permission("zones.manage")), Depends(require_csrf)])
def update_zone(organization_id: str, zone_id: str, payload: ZoneIn, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    validate_origin_or_referer(request)
    _assert_organization_access(organization_id, membership)
    try:
        return {"zone": _serialize_zone_entity(_service(request).update_zone(organization_id, zone_id, payload.site_id, payload.camera_id, payload.zone_type, payload.polygon_json, payload.status, name=payload.name))}
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/organizations/{organization_id}/operations/sites", dependencies=[Depends(require_permission(Permission.VIEW_DASHBOARD))])
def list_sites(organization_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    _assert_organization_access(organization_id, membership)
    return {"items": _serialize_catalog(_service(request), organization_id)["sites"]}


@router.get("/organizations/{organization_id}/operations/cameras", dependencies=[Depends(require_permission(Permission.VIEW_DASHBOARD))])
def list_cameras(organization_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    _assert_organization_access(organization_id, membership)
    return {"items": _serialize_catalog(_service(request), organization_id)["cameras"]}


@router.get("/organizations/{organization_id}/operations/zones", dependencies=[Depends(require_permission(Permission.VIEW_DASHBOARD))])
def list_zones(organization_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    _assert_organization_access(organization_id, membership)
    return {"items": _serialize_catalog(_service(request), organization_id)["zones"]}


@router.get("/organizations/{organization_id}/operations/safety-rules", dependencies=[Depends(require_permission(Permission.VIEW_DASHBOARD))])
def list_safety_rules(organization_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    _assert_organization_access(organization_id, membership)
    return {"items": _serialize_catalog(_service(request), organization_id)["safety_rules"]}


@router.get("/organizations/{organization_id}/operations/required-ppe", dependencies=[Depends(require_permission(Permission.VIEW_DASHBOARD))])
def list_required_ppe(organization_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    _assert_organization_access(organization_id, membership)
    return {"items": _serialize_catalog(_service(request), organization_id)["required_ppe"]}


@router.delete("/organizations/{organization_id}/operations/zones/{zone_id}", status_code=204, dependencies=[Depends(require_permission("zones.manage")), Depends(require_csrf)])
def delete_zone(organization_id: str, zone_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> None:
    _assert_organization_access(organization_id, membership)
    try:
        _service(request).delete_zone(organization_id, zone_id)
    except OperationInUse as exc:
        # 409: o cadastro existe, mas apagá-lo destruiria a rastreabilidade do histórico.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail="zone not found") from exc


@router.delete("/organizations/{organization_id}/operations/cameras/{camera_id}", status_code=204, dependencies=[Depends(require_permission("cameras.manage")), Depends(require_csrf)])
def delete_camera(organization_id: str, camera_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> None:
    _assert_organization_access(organization_id, membership)
    try:
        _service(request).delete_camera(organization_id, camera_id)
    except OperationInUse as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail="camera not found") from exc


@router.delete("/organizations/{organization_id}/operations/sites/{site_id}", status_code=204, dependencies=[Depends(require_permission("sites.manage")), Depends(require_csrf)])
def delete_site(organization_id: str, site_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> None:
    _assert_organization_access(organization_id, membership)
    try:
        _service(request).delete_site(organization_id, site_id)
    except OperationInUse as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=_key_error_status(exc), detail="site not found") from exc
