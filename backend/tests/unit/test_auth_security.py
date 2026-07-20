import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.auth.exceptions import ExpiredTokenError, InvalidTokenError
from app.modules.auth.security import (
    InMemoryLoginRateLimiter,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    password_policy_violations,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self) -> None:
        assert hash_password("Str0ng!Pass") != "Str0ng!Pass"

    def test_verify_succeeds_for_correct_password(self) -> None:
        hashed = hash_password("Str0ng!Pass")
        assert verify_password("Str0ng!Pass", hashed) is True

    def test_verify_fails_for_wrong_password(self) -> None:
        hashed = hash_password("Str0ng!Pass")
        assert verify_password("wrong-password", hashed) is False

    def test_verify_fails_for_malformed_hash(self) -> None:
        assert verify_password("Str0ng!Pass", "not-a-real-hash") is False


class TestPasswordPolicy:
    def test_valid_password_has_no_violations(self) -> None:
        assert password_policy_violations("Str0ng!Pass") == []

    def test_too_short_is_flagged(self) -> None:
        assert any("8 characters" in v for v in password_policy_violations("Ab1!"))

    def test_missing_uppercase_is_flagged(self) -> None:
        assert any("uppercase" in v for v in password_policy_violations("weak1!password"))

    def test_missing_lowercase_is_flagged(self) -> None:
        assert any("lowercase" in v for v in password_policy_violations("WEAK1!PASSWORD"))

    def test_missing_digit_is_flagged(self) -> None:
        assert any("number" in v for v in password_policy_violations("Weak!Password"))

    def test_missing_special_char_is_flagged(self) -> None:
        assert any("special character" in v for v in password_policy_violations("Weak1Password"))


class TestAccessToken:
    def test_round_trip_preserves_claims(self) -> None:
        subject = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_access_token(
            subject=subject,
            tenant_id=tenant_id,
            roles=["admin"],
            permissions=["invoice:issue"],
        )
        payload = decode_access_token(token)
        assert payload.sub == subject
        assert payload.tenant_id == tenant_id
        assert payload.roles == ["admin"]
        assert payload.permissions == ["invoice:issue"]

    def test_expired_token_raises(self) -> None:
        token = create_access_token(
            subject=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            roles=[],
            permissions=[],
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(ExpiredTokenError):
            decode_access_token(token)

    def test_garbage_token_raises_invalid(self) -> None:
        with pytest.raises(InvalidTokenError):
            decode_access_token("not-a-valid-jwt")

    def test_tampered_signature_raises_invalid(self) -> None:
        token = create_access_token(
            subject=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=[], permissions=[]
        )
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(InvalidTokenError):
            decode_access_token(tampered)


class TestRefreshToken:
    def test_generated_tokens_are_unique(self) -> None:
        assert generate_refresh_token() != generate_refresh_token()

    def test_hash_is_deterministic_sha256_hex(self) -> None:
        token = generate_refresh_token()
        digest = hash_refresh_token(token)
        assert digest == hash_refresh_token(token)
        assert len(digest) == 64

    def test_hash_differs_from_raw_token(self) -> None:
        token = generate_refresh_token()
        assert hash_refresh_token(token) != token


class TestInMemoryLoginRateLimiter:
    def test_allows_up_to_max_attempts(self) -> None:
        limiter = InMemoryLoginRateLimiter(max_attempts=3, window=timedelta(minutes=1))
        assert limiter.check_and_record("user@example.com") is True
        assert limiter.check_and_record("user@example.com") is True
        assert limiter.check_and_record("user@example.com") is True

    def test_blocks_after_max_attempts(self) -> None:
        limiter = InMemoryLoginRateLimiter(max_attempts=2, window=timedelta(minutes=1))
        limiter.check_and_record("user@example.com")
        limiter.check_and_record("user@example.com")
        assert limiter.check_and_record("user@example.com") is False

    def test_keys_are_independent(self) -> None:
        limiter = InMemoryLoginRateLimiter(max_attempts=1, window=timedelta(minutes=1))
        assert limiter.check_and_record("a@example.com") is True
        assert limiter.check_and_record("b@example.com") is True

    def test_reset_clears_the_key(self) -> None:
        limiter = InMemoryLoginRateLimiter(max_attempts=1, window=timedelta(minutes=1))
        limiter.check_and_record("user@example.com")
        limiter.reset("user@example.com")
        assert limiter.check_and_record("user@example.com") is True

    def test_window_expiry_allows_new_attempts(self) -> None:
        limiter = InMemoryLoginRateLimiter(max_attempts=1, window=timedelta(minutes=1))
        # Simulate a window that started far enough in the past to have elapsed.
        limiter._hits["user@example.com"] = (datetime.now(UTC) - timedelta(minutes=5), 1)
        assert limiter.check_and_record("user@example.com") is True
