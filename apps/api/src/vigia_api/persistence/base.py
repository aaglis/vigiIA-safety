from __future__ import annotations

try:
    from sqlalchemy.orm import DeclarativeBase
except Exception:  # pragma: no cover
    DeclarativeBase = object  # type: ignore[misc,assignment]


class Base(DeclarativeBase):  # type: ignore[misc]
    pass
