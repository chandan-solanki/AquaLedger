from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.request_context import RequestContext
from app.core.document_engine.exceptions import DocumentNotFoundError
from app.core.document_engine.reportlab_support import build_logo_flowable
from app.core.document_engine.storage import LocalStorageService, StorageService
from app.core.errors import AppException, ConflictError
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import UserProfileResponse
from app.modules.auth.service import AuthService
from app.modules.profile.constants import (
    ALLOWED_AVATAR_CONTENT_TYPES,
    AVATAR_EXTENSION_BY_CONTENT_TYPE,
    MAX_AVATAR_SIZE_BYTES,
)
from app.modules.profile.exceptions import (
    AvatarNotFoundError,
    AvatarTooLargeError,
    InvalidAvatarContentTypeError,
)
from app.modules.profile.schemas import ProfileUpdateRequest
from app.modules.users.exceptions import DuplicateUsernameError


def _build_avatar_storage_key(user: User, content_type: str) -> str:
    """One deterministic key per user - a re-upload naturally replaces the
    previous avatar in place. Tenant-prefixed for the same reason every
    other storage key in this codebase is (build_document_storage_key,
    company_profile's _build_logo_storage_key): keeps one tenant's files
    visibly and structurally apart from another's on disk, even though
    user.id (a UUID7) is already globally unique on its own."""
    extension = AVATAR_EXTENSION_BY_CONTENT_TYPE[content_type]
    return f"{user.tenant_id}/users/{user.id}/avatar{extension}"


class ProfileService:
    """Self-service operations on the CALLER's own account only - every
    method takes the already-authenticated `User` ORM object straight from
    `get_current_user`, never a client-supplied id, so there is no query
    path here that could touch another user's row.

    No repository.py: unlike company_profile (which owns the
    company_profiles table), this module owns no table of its own - every
    mutation is a direct attribute change on the already-loaded `User` row
    the router already has, exactly like AuthService.change_password
    receives the loaded `User` rather than re-fetching it. Introducing a
    repository layer with nothing to query would be an empty abstraction.
    """

    def __init__(
        self,
        session: AsyncSession,
        auth_service: AuthService,
        storage: StorageService | None = None,
    ) -> None:
        self._session = session
        self._auth_service = auth_service
        self._auth_repo = AuthRepository(session)
        self._storage = storage or LocalStorageService()

    async def update_profile(
        self, user: User, payload: ProfileUpdateRequest, *, ctx: RequestContext
    ) -> UserProfileResponse:
        changed_fields = payload.model_dump(exclude_unset=True)
        old_values = {field: getattr(user, field) for field in changed_fields}
        for field, value in changed_fields.items():
            setattr(user, field, value)

        if changed_fields:
            # Staged alongside the field changes so a failed commit (e.g. a
            # duplicate-username constraint) rolls both back together - no
            # audit row survives for a mutation that didn't actually happen
            # (mirrors UserService.update's identical ordering).
            await self._auth_repo.add_audit_log(
                tenant_id=user.tenant_id,
                user_id=user.id,
                action="profile_updated",
                entity_type="user",
                entity_id=user.id,
                changes={
                    field: {"old": old_values[field], "new": value}
                    for field, value in changed_fields.items()
                },
                ip_address=ctx.ip,
                user_agent=ctx.user_agent,
                request_id=ctx.request_id,
            )
        await self._commit_or_raise()
        await self._session.refresh(user)
        return await self._auth_service.get_profile(user)

    async def upload_avatar(
        self, user: User, *, content: bytes, content_type: str, ctx: RequestContext
    ) -> UserProfileResponse:
        if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
            raise InvalidAvatarContentTypeError(
                f"Unsupported avatar content type: {content_type!r}. "
                f"Allowed: {', '.join(sorted(ALLOWED_AVATAR_CONTENT_TYPES))}"
            )
        if len(content) > MAX_AVATAR_SIZE_BYTES:
            raise AvatarTooLargeError(
                f"Avatar exceeds the maximum size of {MAX_AVATAR_SIZE_BYTES} bytes"
            )
        if build_logo_flowable(content, max_width=1, max_height=1) is None:
            # Content-Type is a client-supplied header, not a guarantee the
            # bytes actually decode as an image - reuses the exact decoder
            # company_profile's logo upload already trusts (Sprint 12's
            # reportlab_support.build_logo_flowable), so a corrupt/truncated
            # upload is rejected here rather than silently stored and only
            # discovered broken the next time it's rendered.
            raise InvalidAvatarContentTypeError(
                "The uploaded file could not be decoded as a valid image"
            )

        new_key = _build_avatar_storage_key(user, content_type)
        old_key = user.avatar_storage_key

        # Storage write happens before the DB update, and DB update before
        # commit - LocalStorageService has no transaction to join, so this
        # ordering is the compensation strategy: if `save` itself raises,
        # the DB is untouched (no broken reference is ever persisted). If
        # the later commit fails for some other reason, the new file can be
        # left orphaned on disk, but the DB still points at whatever it
        # pointed at before (old_key, still valid) - never at a file that
        # doesn't exist. The old file is deleted only after the new one is
        # safely written and the extension actually changed.
        self._storage.save(new_key, content, content_type=content_type)
        if old_key and old_key != new_key:
            self._storage.delete(old_key)

        user.avatar_storage_key = new_key
        user.avatar_content_type = content_type
        user.avatar_uploaded_at = datetime.now(UTC)
        await self._auth_repo.add_audit_log(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="avatar_uploaded",
            entity_type="user",
            entity_id=user.id,
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()
        await self._session.refresh(user)
        return await self._auth_service.get_profile(user)

    async def delete_avatar(self, user: User, *, ctx: RequestContext) -> None:
        if not user.avatar_storage_key:
            raise AvatarNotFoundError("You have no avatar to remove")

        self._storage.delete(user.avatar_storage_key)
        user.avatar_storage_key = None
        user.avatar_content_type = None
        user.avatar_uploaded_at = None
        await self._auth_repo.add_audit_log(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="avatar_removed",
            entity_type="user",
            entity_id=user.id,
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
        await self._session.commit()

    async def load_avatar_bytes(self, user: User) -> tuple[bytes, str]:
        """Used only by GET /profile/avatar - raises AvatarNotFoundError
        rather than tolerating a missing file, since an explicit avatar
        request should surface a real 404 instead of rendering nothing."""
        if not user.avatar_storage_key or not user.avatar_content_type:
            raise AvatarNotFoundError("You have no avatar")

        try:
            content = self._storage.load(user.avatar_storage_key)
        except DocumentNotFoundError as exc:
            # DB and storage can drift apart (storage writes/deletes aren't
            # transactional with the DB) - self-heal by clearing the stale
            # reference, mirroring CompanyProfileService.load_logo_bytes.
            user.avatar_storage_key = None
            user.avatar_content_type = None
            user.avatar_uploaded_at = None
            await self._session.commit()
            raise AvatarNotFoundError("The stored avatar file is no longer available") from exc
        return content, user.avatar_content_type

    async def _commit_or_raise(self) -> None:
        """Commit, translating a unique-constraint violation into a clean
        409 - mirrors UserService._commit_or_raise (check-then-insert races
        the constraint itself resolves, not a pre-check SELECT)."""
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_users_tenant_username":
            return DuplicateUsernameError("A user with this username already exists")
        return ConflictError("This operation conflicts with existing data")
