from __future__ import annotations

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except Exception:  # pragma: no cover
    create_engine = None  # type: ignore[assignment]
    sessionmaker = None  # type: ignore[assignment]

from ..settings import settings


def get_engine(url: str | None = None):
    if create_engine is None:
        return None
    return create_engine(url or settings.database_url, pool_pre_ping=True, future=True)


def get_session_factory(url: str | None = None):
    engine = get_engine(url)
    if engine is None or sessionmaker is None:
        return None
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
