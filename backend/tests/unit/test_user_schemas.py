import uuid

import pytest
from pydantic import ValidationError

from app.modules.auth.constants import AccountStatus
from app.modules.users.schemas import (
    UserCreateRequest,
    UserListParams,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)

_MINIMAL: dict[str, object] = {
    "email": "priya@fisherp.local",
    "username": "priya",
    "full_name": "Priya Nair",
    "password": "TempPass@123",
    "role_id": uuid.uuid4(),
}


class TestUserCreateRequestValidation:
    def test_minimal_payload_is_accepted(self) -> None:
        request = UserCreateRequest(**_MINIMAL)
        assert request.email == "priya@fisherp.local"
        assert request.phone is None

    def test_email_is_lowercased(self) -> None:
        request = UserCreateRequest(**{**_MINIMAL, "email": "Priya@FishERP.Local"})
        assert request.email == "priya@fisherp.local"

    @pytest.mark.parametrize(
        "value", ["not-an-email", "missing-domain@", "@missing-local.com", "no-at-sign"]
    )
    def test_rejects_malformed_emails(self, value: str) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest(**{**_MINIMAL, "email": value})

    @pytest.mark.parametrize("value", ["9876543210", "+919876543210", "1234567"])
    def test_accepts_valid_phone_numbers(self, value: str) -> None:
        request = UserCreateRequest(**_MINIMAL, phone=value)
        assert request.phone == value

    @pytest.mark.parametrize("value", ["123", "abcdefghij", "98765-43210"])
    def test_rejects_invalid_phone_numbers(self, value: str) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest(**_MINIMAL, phone=value)

    def test_username_is_lowercased(self) -> None:
        request = UserCreateRequest(**{**_MINIMAL, "username": "Priya.Nair"})
        assert request.username == "priya.nair"

    @pytest.mark.parametrize("value", ["ab", "has space", "has$symbol", "x" * 101])
    def test_rejects_invalid_usernames(self, value: str) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest(**{**_MINIMAL, "username": value})

    def test_rejects_short_password(self) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest(**{**_MINIMAL, "password": "short"})

    def test_rejects_blank_full_name(self) -> None:
        with pytest.raises(ValidationError):
            UserCreateRequest(**{**_MINIMAL, "full_name": ""})

    def test_has_no_is_superuser_field(self) -> None:
        """is_superuser must never be settable through this request - not a
        field the client can send at all, not just server-ignored."""
        assert "is_superuser" not in UserCreateRequest.model_fields

    def test_has_no_status_field(self) -> None:
        assert "status" not in UserCreateRequest.model_fields


class TestUserUpdateRequestValidation:
    def test_all_fields_optional(self) -> None:
        request = UserUpdateRequest()
        assert request.model_dump(exclude_unset=True) == {}

    def test_rejects_malformed_email(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(email="not-an-email")

    def test_none_email_is_allowed(self) -> None:
        request = UserUpdateRequest(email=None)
        assert request.email is None

    def test_has_no_password_field(self) -> None:
        """Admin-triggered password resets aren't supported by the existing
        architecture - only self-service /auth/change-password exists."""
        assert "password" not in UserUpdateRequest.model_fields

    def test_has_no_status_field(self) -> None:
        """Status changes go through PATCH /users/{id}/status, not this one."""
        assert "status" not in UserUpdateRequest.model_fields


class TestUserStatusUpdateRequest:
    def test_accepts_active(self) -> None:
        assert UserStatusUpdateRequest(status=AccountStatus.ACTIVE).status == AccountStatus.ACTIVE

    def test_accepts_inactive(self) -> None:
        request = UserStatusUpdateRequest(status=AccountStatus.INACTIVE)
        assert request.status == AccountStatus.INACTIVE

    @pytest.mark.parametrize("value", ["locked", "password_expired", "not-a-status"])
    def test_rejects_system_managed_or_unknown_statuses(self, value: str) -> None:
        """locked/password_expired are driven by AuthService's login/lockout
        logic, not an administrator action through this endpoint."""
        with pytest.raises(ValidationError):
            UserStatusUpdateRequest(status=value)


class TestUserListParams:
    def test_defaults(self) -> None:
        params = UserListParams()
        assert params.sort == "-created_at"
        assert params.page == 1
        assert params.page_size == 20

    @pytest.mark.parametrize(
        "sort", ["full_name", "-full_name", "email", "username", "-created_at", "last_login_at"]
    )
    def test_accepts_sortable_fields(self, sort: str) -> None:
        assert UserListParams(sort=sort).sort == sort

    def test_rejects_unknown_sort_field(self) -> None:
        with pytest.raises(ValidationError):
            UserListParams(sort="password_hash")
