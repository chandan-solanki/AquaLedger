import datetime as dt

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class INETString(TypeDecorator[str]):
    """Postgres INET, but always a plain str on the Python side.

    Read back through asyncpg, a bare INET column deserializes to
    ipaddress.IPv4Address/IPv6Address, not str - which silently breaks any
    code (or Pydantic schema) that expects a string. Every part of this app
    that stores an IP (refresh_tokens.ip, audit_logs.ip_address, ...) treats
    it as a string, so this keeps that true on read as well as on write.
    """

    impl = INET
    cache_ok = True

    def process_result_value(self, value: object, dialect: object) -> str | None:
        return str(value) if value is not None else None


class TimestampMixin:
    """created_at / updated_at columns shared by mutable tables."""

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
