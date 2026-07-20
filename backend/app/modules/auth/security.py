import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.modules.auth.exceptions import ExpiredTokenError, InvalidTokenError
from app.modules.auth.schemas import AccessTokenPayload

settings = get_settings()
_hasher = PasswordHasher()

_SPECIAL_CHARS = re.compile(r"""[!@#$%^&*()_+\-=\[\]{};:'"\\|,.<>/?`~]""")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_policy_violations(password: str) -> list[str]:
    """Pure check against the configured password policy - does not raise.

    Returns a list of human-readable violations; empty list means the
    password satisfies the policy.
    """
    violations = []
    if len(password) < settings.password_min_length:
        violations.append(
            f"Password must be at least {settings.password_min_length} characters long"
        )
    if not any(c.isupper() for c in password):
        violations.append("Password must contain an uppercase letter")
    if not any(c.islower() for c in password):
        violations.append("Password must contain a lowercase letter")
    if not any(c.isdigit() for c in password):
        violations.append("Password must contain a number")
    if not _SPECIAL_CHARS.search(password):
        violations.append("Password must contain a special character")
    return violations


def generate_refresh_token() -> str:
    """Opaque 256-bit token returned to the client. Never stored raw."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest for storage in refresh_tokens.token_hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    *,
    subject: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str],
    permissions: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "permissions": permissions,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> AccessTokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredTokenError("Access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Access token is invalid") from exc
    return AccessTokenPayload.model_validate(payload)


class InMemoryLoginRateLimiter:
    """Fixed-window request counter keyed by an arbitrary string (e.g. email+ip).

    Process-local only - does not share state across multiple workers/instances.
    Swap for a Redis-backed implementation behind the same interface once
    Redis is provisioned; callers should not need to change.
    """

    def __init__(self, max_attempts: int, window: timedelta) -> None:
        self._max_attempts = max_attempts
        self._window = window
        self._hits: dict[str, tuple[datetime, int]] = {}

    def check_and_record(self, key: str) -> bool:
        """Record an attempt for `key`, returning False once over the limit."""
        now = datetime.now(UTC)
        window_start, count = self._hits.get(key, (now, 0))
        if now - window_start > self._window:
            window_start, count = now, 0
        count += 1
        self._hits[key] = (window_start, count)
        return count <= self._max_attempts

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


login_rate_limiter = InMemoryLoginRateLimiter(
    max_attempts=settings.login_rate_limit_attempts,
    window=timedelta(minutes=settings.login_rate_limit_window_minutes),
)
