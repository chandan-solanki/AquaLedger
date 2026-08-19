import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.audit_logs.service import AuditLogService
from app.modules.auth.models import AuditLog, User


def _make_user(**overrides: Any) -> User:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "email": "admin@fisherp.local",
        "username": "admin",
        "password_hash": "hash",
        "full_name": "Super Admin",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return User(**defaults)


def _make_log(**overrides: Any) -> AuditLog:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "user_id": None,
        "user": None,
        "action": "user_created",
        "entity_type": "user",
        "entity_id": uuid.uuid4(),
        "changes": None,
        "ip_address": "127.0.0.1",
        "user_agent": "pytest",
        "request_id": "req-1",
        "created_at": now,
    }
    defaults.update(overrides)
    return AuditLog(**defaults)


class TestToListItem:
    def test_maps_fields_with_actor(self) -> None:
        actor = _make_user(full_name="Priya Nair", email="priya@fisherp.local")
        log = _make_log(user=actor, user_id=actor.id, changes={"email": "priya@fisherp.local"})

        item = AuditLogService._to_list_item(log)

        assert item.id == log.id
        assert item.tenant_id == log.tenant_id
        assert item.actor is not None
        assert item.actor.id == actor.id
        assert item.actor.full_name == "Priya Nair"
        assert item.actor.email == "priya@fisherp.local"
        assert item.action == "user_created"
        assert item.entity_type == "user"
        assert item.entity_id == log.entity_id
        assert item.changes == {"email": "priya@fisherp.local"}
        assert item.ip_address == "127.0.0.1"
        assert item.user_agent == "pytest"

    def test_null_actor_when_log_has_no_user(self) -> None:
        """AuditLog.user_id is nullable - e.g. a failed login against an
        email that doesn't belong to any account."""
        log = _make_log(user=None, user_id=None, action="login_failed")

        item = AuditLogService._to_list_item(log)

        assert item.actor is None

    def test_actor_never_leaks_password_hash(self) -> None:
        actor = _make_user()
        log = _make_log(user=actor, user_id=actor.id)

        item = AuditLogService._to_list_item(log)

        assert not hasattr(item.actor, "password_hash")

    def test_changes_pass_through_unmodified(self) -> None:
        changes = {"status": {"old": "active", "new": "inactive"}}
        log = _make_log(changes=changes)

        item = AuditLogService._to_list_item(log)

        assert item.changes == changes
