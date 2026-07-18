from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..settings import settings


def get_engine(url: str | None = None):
    return create_engine(url or settings.database_url, pool_pre_ping=True, future=True)


def get_session_factory(url: str | None = None):
    engine = get_engine(url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
