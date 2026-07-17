from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .domain.edge_workers import EdgeWorker
from .persistence.session import get_session_factory
from .services.account_recovery import AccountRecoveryService
from typing import Any

from .services.auth import AuthService, InMemoryAuthRepository
from .services.edge_workers import EdgeWorkerService, InMemoryEdgeWorkerRepository
from .services.evidence import EvidenceService, InMemoryEvidenceMetadataRepository
from .services.incidents import InMemoryIncidentRepository
from .services.invites import InviteService
from .services.platform_admin import PlatformAdminService
from .services.security import hash_token
from .services.detection_stream import DetectionHub
from .settings import Settings, settings
from .services.operations import InMemoryOperationsRepository

RepositoryBackend = Literal["memory", "postgres"]


@dataclass
class AppContainer:
    settings: Settings
    repository_backend: RepositoryBackend
    auth_repository: Any
    auth_service: AuthService
    account_recovery_service: Any
    invite_service: Any
    platform_admin_service: Any
    incident_repository: object
    edge_worker_repository: object
    edge_worker_service: EdgeWorkerService
    evidence_metadata_repository: object
    evidence_service: EvidenceService
    operations_repository: Any
    detection_hub: Any = None
    session_factory: object | None = None


def _resolve_backend(config: Settings) -> RepositoryBackend:
    backend = config.repository_backend.lower().strip()
    if backend not in {"memory", "postgres"}:
        raise ValueError("REPOSITORY_BACKEND must be 'memory' or 'postgres'")
    return backend  # type: ignore[return-value]


def build_container(config: Settings | None = None, *, repository_backend: str | None = None, seed_dev: bool = True) -> AppContainer:
    config = config or settings
    backend = _resolve_backend(config if repository_backend is None else config.model_copy(update={"repository_backend": repository_backend}))
    session_factory = get_session_factory(config.database_url) if backend == "postgres" else None

    auth_repository = InMemoryAuthRepository()
    if backend == "postgres":
        from .persistence.auth_repository import SqlAlchemyAuthRepository
        from .persistence.operations_repository import SqlAlchemyOperationsRepository
        from .persistence.repositories import SqlAlchemyEdgeWorkerRepository, SqlAlchemyEvidenceRepository, SqlAlchemyIncidentRepository

        from .persistence.invite_repository import SqlAlchemyInviteRepository
        from .persistence.platform_repository import SqlAlchemyPlatformRepository
        from .persistence.account_recovery_repository import SqlAlchemyAccountRecoveryRepository

        incident_repository = SqlAlchemyIncidentRepository(session_factory, app_settings=config)
        edge_worker_repository = SqlAlchemyEdgeWorkerRepository(session_factory)
        evidence_metadata_repository = SqlAlchemyEvidenceRepository(session_factory)
        operations_repository = SqlAlchemyOperationsRepository(session_factory)
        auth_repository = SqlAlchemyAuthRepository(session_factory)
        invite_repository = SqlAlchemyInviteRepository(session_factory)
        platform_repository = SqlAlchemyPlatformRepository(session_factory)
        recovery_repository = SqlAlchemyAccountRecoveryRepository(session_factory)
    else:
        invite_repository = None
        platform_repository = None
        recovery_repository = None
        incident_repository = InMemoryIncidentRepository(app_settings=config)
        edge_worker_repository = InMemoryEdgeWorkerRepository()
        evidence_metadata_repository = InMemoryEvidenceMetadataRepository()
        operations_repository = InMemoryOperationsRepository()
        # O repo em memória não conhece incidentes; injeta a checagem para que excluir
        # câmera/zona com histórico seja barrado igual ao backend SQL.
        operations_repository._incident_lookup = lambda kind, value: any(
            (getattr(i, "camera_id", None) == value if kind == "camera" else getattr(i, "zone_id", None) == value)
            for i in getattr(incident_repository, "incidents", {}).values()
        )
    auth_service = AuthService(repository=auth_repository, config=config)
    evidence_service = EvidenceService(metadata_repository=evidence_metadata_repository)
    edge_worker_service = EdgeWorkerService(incident_repository=incident_repository, repository=edge_worker_repository, evidence_service=evidence_service, operations_repository=operations_repository)
    container = AppContainer(
        settings=config,
        repository_backend=backend,
        auth_repository=auth_repository,
        auth_service=auth_service,
        account_recovery_service=AccountRecoveryService(auth_repository, repository=recovery_repository),
        invite_service=InviteService(auth_repository, repository=invite_repository),
        platform_admin_service=PlatformAdminService(auth_repository, repository=platform_repository),
        incident_repository=incident_repository,
        edge_worker_repository=edge_worker_repository,
        edge_worker_service=edge_worker_service,
        evidence_metadata_repository=evidence_metadata_repository,
        evidence_service=evidence_service,
        detection_hub=DetectionHub(),
        operations_repository=operations_repository,
        session_factory=session_factory,
    )
    if seed_dev:
        bootstrap_dev_seed(container)
    return container


def bootstrap_dev_seed(container: AppContainer) -> None:
    """Register deterministic dev-only data without hiding it in import side effects."""
    if container.settings.app_env.lower() != "dev":
        return
    existing = container.edge_worker_service.repository.get_by_client_id(container.settings.edge_worker_client_id)
    if existing is not None:
        container.edge_worker_service.camera_catalog[(existing.organization_id, existing.site_id)] = set(existing.allowed_camera_ids)
        return
    worker = EdgeWorker(
        id="edge-worker-demo",
        organization_id="org-demo",
        site_id="site-demo",
        name="Edge Worker Demo",
        client_id=container.settings.edge_worker_client_id,
        api_key_hash=hash_token(container.settings.edge_worker_api_key),
        allowed_camera_ids=["camera-demo-01"],
    )
    container.edge_worker_service.repository.save(worker)
    container.edge_worker_service.camera_catalog[(worker.organization_id, worker.site_id)] = set(worker.allowed_camera_ids)


default_container = build_container(settings, seed_dev=settings.repository_backend.lower() != "postgres")

# Backwards-compatible aliases for legacy tests/imports. New code should use
# request.app.state.container or build_container()/create_app().
incident_repository = default_container.incident_repository
edge_worker_service = default_container.edge_worker_service
