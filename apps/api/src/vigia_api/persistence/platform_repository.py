from __future__ import annotations

from datetime import datetime, timezone

try:
    from sqlalchemy import select  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    select = None  # type: ignore[assignment]

from ..domain.platform import Organization, OrganizationStatus
from .models import Organization as OrganizationRow


class SqlAlchemyPlatformRepository:
    """Organizações da plataforma persistidas. O audit do platform-admin segue em memória
    (ver knownLimitations do card): não há tabela platform_audit_logs ainda."""

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def _ensure_aware(self, value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _to_domain(self, row: OrganizationRow | None) -> Organization | None:
        if row is None:
            return None
        return Organization(
            id=row.id,
            name=row.name,
            legal_name=row.legal_name,
            tax_id=row.tax_id,
            status=OrganizationStatus(row.status),
            plan=row.plan,
            retention_days=row.retention_days,
            created_by_user_id=row.created_by_user_id or "",
            created_at=self._ensure_aware(row.created_at),
            updated_at=self._ensure_aware(row.updated_at),
        )

    def save(self, organization: Organization) -> None:
        with self.session_factory() as session:
            session.merge(
                OrganizationRow(
                    id=organization.id,
                    name=organization.name,
                    legal_name=organization.legal_name,
                    tax_id=organization.tax_id,
                    status=organization.status.value,
                    retention_days=organization.retention_days,
                    plan=organization.plan,
                    created_by_user_id=organization.created_by_user_id or None,
                    created_at=organization.created_at,
                    updated_at=organization.updated_at,
                )
            )
            session.commit()

    def get(self, organization_id: str) -> Organization | None:
        with self.session_factory() as session:
            return self._to_domain(session.get(OrganizationRow, organization_id))

    def list_all(self) -> list[Organization]:
        if select is None:
            return []
        with self.session_factory() as session:
            rows = session.execute(select(OrganizationRow)).scalars().all()
            return [org for org in (self._to_domain(row) for row in rows) if org is not None]
