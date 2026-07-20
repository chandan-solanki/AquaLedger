import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import ChangePasswordRequest, LoginRequest, RefreshTokenRequest


class TestLoginRequestEmailValidation:
    def test_accepts_a_normal_email(self) -> None:
        request = LoginRequest(email="user@example.com", password="x")
        assert request.email == "user@example.com"

    def test_accepts_the_reserved_local_tld(self) -> None:
        # admin@fisherp.local is the seeded super admin (ARCHITECTURE §5.2) -
        # email-validator's default rules reject .local as a reserved TLD,
        # which is why LoginRequest uses a structural regex instead.
        request = LoginRequest(email="admin@fisherp.local", password="x")
        assert request.email == "admin@fisherp.local"

    def test_normalizes_case(self) -> None:
        request = LoginRequest(email="Admin@Fisherp.Local", password="x")
        assert request.email == "admin@fisherp.local"

    def test_strips_whitespace(self) -> None:
        request = LoginRequest(email="  admin@fisherp.local  ", password="x")
        assert request.email == "admin@fisherp.local"

    @pytest.mark.parametrize(
        "value",
        ["not-an-email", "missing-domain@", "@missing-local.com", "no-at-sign.com", ""],
    )
    def test_rejects_malformed_addresses(self, value: str) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(email=value, password="x")

    def test_rejects_missing_password(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com", password="")


class TestRefreshTokenRequest:
    def test_rejects_empty_token(self) -> None:
        with pytest.raises(ValidationError):
            RefreshTokenRequest(refresh_token="")

    def test_accepts_a_token(self) -> None:
        request = RefreshTokenRequest(refresh_token="opaque-value")
        assert request.refresh_token == "opaque-value"


class TestChangePasswordRequest:
    def test_rejects_new_password_shorter_than_eight_chars(self) -> None:
        with pytest.raises(ValidationError):
            ChangePasswordRequest(current_password="x", new_password="Ab1!")

    def test_accepts_a_password_meeting_the_length_floor(self) -> None:
        # Pydantic only enforces the length floor here; the full policy
        # (upper/lower/digit/special) is enforced in the service layer via
        # password_policy_violations, not at the schema layer.
        request = ChangePasswordRequest(current_password="x", new_password="password")
        assert request.new_password == "password"
