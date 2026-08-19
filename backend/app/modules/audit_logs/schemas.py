import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SORTABLE_FIELDS = frozenset({"created_at"})


class AuditLogActor(BaseModel):
    """Snapshot of the user who performed the action. No password_hash or
    any other credential field is ever exposed here."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class AuditLogListItem(BaseModel):
    """actor is null for records with no associated user (AuditLog.user_id
    is nullable - e.g. a failed login against an unknown email)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "019f9a12-1234-7abc-9def-0123456789ab",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "actor": {
                    "id": "019f7af3-9000-7abc-9def-0123456789ab",
                    "full_name": "Super Admin",
                    "email": "admin@fisherp.local",
                },
                "action": "user_created",
                "entity_type": "user",
                "entity_id": "019f9a12-1234-7abc-9def-0123456789ab",
                "changes": {"email": "priya@fisherp.local", "role": "accountant"},
                "ip_address": "127.0.0.1",
                "user_agent": "Mozilla/5.0",
                "created_at": "2026-08-17T09:48:08.714017Z",
            }
        }
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    actor: AuditLogActor | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    changes: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogListParams(BaseModel):
    """Query params for GET /audit-logs.

    `q` searches the acting user's full_name, email and username (case-
    insensitive substring) - audit_logs itself has no other free-text field
    worth searching. `from_date`/`to_date` bound created_at's date,
    inclusive on both ends, matching DocumentListParams' convention.
    """

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across the actor's full_name, email and username.",
        examples=["priya"],
    )
    action: str | None = Field(default=None, max_length=100, examples=["user_created"])
    entity_type: str | None = Field(default=None, max_length=100, examples=["user"])
    user_id: uuid.UUID | None = Field(default=None, description="Filter by the acting user.")
    from_date: date | None = Field(
        default=None, description="Inclusive lower bound on created_at's date."
    )
    to_date: date | None = Field(
        default=None, description="Inclusive upper bound on created_at's date."
    )
    sort: str = Field(
        default="-created_at",
        description="created_at; prefix with '-' for descending.",
        examples=["created_at", "-created_at"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("sort")
    @classmethod
    def _check_sort(cls, value: str) -> str:
        field = value[1:] if value.startswith("-") else value
        if field not in _SORTABLE_FIELDS:
            raise ValueError(
                f"Invalid sort field '{field}'. Allowed: {', '.join(sorted(_SORTABLE_FIELDS))}"
            )
        return value

    @model_validator(mode="after")
    def _check_date_range(self) -> "AuditLogListParams":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must not be after to_date")
        return self
