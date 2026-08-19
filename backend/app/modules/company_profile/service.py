import uuid
from datetime import UTC, datetime
from typing import NamedTuple

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_engine.exceptions import DocumentNotFoundError, InvalidStorageKeyError
from app.core.document_engine.reportlab_support import build_logo_flowable
from app.core.document_engine.storage import LocalStorageService, StorageService
from app.modules.auth.models import Tenant
from app.modules.company_profile.constants import (
    ALLOWED_LOGO_CONTENT_TYPES,
    LOGO_EXTENSION_BY_CONTENT_TYPE,
    MAX_LOGO_SIZE_BYTES,
)
from app.modules.company_profile.exceptions import (
    InvalidLogoContentTypeError,
    LogoNotFoundError,
    LogoTooLargeError,
)
from app.modules.company_profile.models import CompanyProfile
from app.modules.company_profile.repository import CompanyProfileRepository
from app.modules.company_profile.schemas import CompanyProfileResponse, CompanyProfileUpsertRequest

logger = structlog.get_logger("app.company_profile")

_LOGO_URL_PATH = "/company-profile/logo"


class CompanyProfileDocumentContext(NamedTuple):
    """What the 6 document-generating modules (and report export) need
    to brand a generated PDF with the tenant's own identity - resolved
    once per document generation via CompanyProfileService.get_document_context,
    never once per line item. All fields are None (never raised) when
    the tenant has no profile row yet, or its logo file has drifted out
    of storage - document generation must never fail on a missing
    profile. display_name is the profile's own display_name (falling
    back to its legal_name) - callers should prefer it over the raw
    Tenant.name once it is non-None, so a tenant that has set up its
    Company Profile sees that identity on generated documents instead
    of the tenant record's internal name."""

    display_name: str | None
    tenant_details: str | None
    logo_bytes: bytes | None
    logo_content_type: str | None


def _build_logo_storage_key(tenant_id: uuid.UUID, content_type: str) -> str:
    """One deterministic key per tenant - a re-upload naturally replaces
    the previous logo in place. Not built via
    app.core.document_engine.storage.build_document_storage_key: that
    helper is scoped to the closed DocumentType enum (invoice, purchase
    bill, ...), and a logo is not one of this engine's business
    documents."""
    extension = LOGO_EXTENSION_BY_CONTENT_TYPE[content_type]
    return f"{tenant_id}/company-profile/logo{extension}"


def _format_tenant_details(profile: CompanyProfile) -> str | None:
    """Builds the address/GSTIN/contact block printed under the tenant
    name on every generated document - the exact <br/>-joined-lines
    convention every document_renderer.py's own _build_header() already
    uses for its right-hand column, not a new markup convention."""
    state_and_pincode = " ".join(part for part in (profile.state, profile.pincode) if part)
    lines = [
        profile.address_line1,
        profile.address_line2,
        state_and_pincode or None,
        profile.city,
        profile.country,
    ]
    if profile.gstin:
        lines.append(f"GSTIN: {profile.gstin}")
    if profile.pan:
        lines.append(f"PAN: {profile.pan}")
    if profile.phone:
        lines.append(f"Phone: {profile.phone}")
    if profile.email:
        lines.append(f"Email: {profile.email}")
    non_empty = [line for line in lines if line]
    return "<br/>".join(non_empty) if non_empty else None


class CompanyProfileService:
    def __init__(self, session: AsyncSession, storage: StorageService | None = None) -> None:
        self._session = session
        self._repo = CompanyProfileRepository(session)
        self._storage = storage or LocalStorageService()

    async def get(self, *, tenant_id: uuid.UUID) -> CompanyProfileResponse:
        """Returns the tenant's profile, auto-vivifying an empty one
        (seeded from Tenant.name) on first access - the settings page
        only ever needs one PUT-based form, never a separate create
        step. A race between two concurrent first-GETs for the same
        brand-new tenant is resolved by catching the unique tenant_id
        violation and re-fetching, not by locking."""
        profile = await self._get_or_vivify(tenant_id)
        return self._to_response(profile)

    async def get_or_none(self, *, tenant_id: uuid.UUID) -> CompanyProfile | None:
        """Raw lookup, never auto-vivifies and never raises - used only
        by get_document_context, which must tolerate a tenant with no
        profile row at all."""
        return await self._repo.get_by_tenant(tenant_id)

    async def upsert(
        self,
        payload: CompanyProfileUpsertRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> CompanyProfileResponse:
        profile = await self._get_or_vivify(tenant_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        profile.updated_by = actor_id
        await self._session.commit()
        await self._session.refresh(profile)
        return self._to_response(profile)

    async def upload_logo(
        self, tenant_id: uuid.UUID, *, content: bytes, content_type: str
    ) -> CompanyProfileResponse:
        if content_type not in ALLOWED_LOGO_CONTENT_TYPES:
            raise InvalidLogoContentTypeError(
                f"Unsupported logo content type: {content_type!r}. "
                f"Allowed: {', '.join(sorted(ALLOWED_LOGO_CONTENT_TYPES))}"
            )
        if len(content) > MAX_LOGO_SIZE_BYTES:
            raise LogoTooLargeError(f"Logo exceeds the maximum size of {MAX_LOGO_SIZE_BYTES} bytes")
        if build_logo_flowable(content, max_width=1, max_height=1) is None:
            # Content-Type is a client-supplied header, not a guarantee the
            # bytes actually decode as an image - reusing the exact decoder
            # the 6 business-document PDFs already trust (Sprint 12
            # reportlab_support.build_logo_flowable) means a file accepted
            # here is one those renderers can later draw, not just one that
            # LooksLikeAnImage per its declared header. Without this check
            # a corrupt/truncated upload would still be accepted here, then
            # silently render with no logo on the 6 PDFs (which already
            # tolerate a bad logo) but crash every WeasyPrint report/
            # statement export for the tenant instead (report_export's
            # pdf_exporter.py has no equivalent tolerance).
            raise InvalidLogoContentTypeError(
                "The uploaded file could not be decoded as a valid image"
            )

        profile = await self._get_or_vivify(tenant_id)
        new_key = _build_logo_storage_key(tenant_id, content_type)
        if profile.logo_storage_key and profile.logo_storage_key != new_key:
            # Extension changed (e.g. a previous PNG replaced by a JPEG) -
            # delete the old key first so it doesn't linger as an orphan
            # file; a same-extension re-upload just overwrites new_key.
            self._storage.delete(profile.logo_storage_key)

        self._storage.save(new_key, content, content_type=content_type)
        profile.logo_storage_key = new_key
        profile.logo_content_type = content_type
        profile.logo_uploaded_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(profile)
        return self._to_response(profile)

    async def delete_logo(self, tenant_id: uuid.UUID) -> None:
        profile = await self._get_or_vivify(tenant_id)
        if not profile.logo_storage_key:
            raise LogoNotFoundError("This tenant has no logo to remove")
        self._storage.delete(profile.logo_storage_key)
        profile.logo_storage_key = None
        profile.logo_content_type = None
        profile.logo_uploaded_at = None
        await self._session.commit()

    async def load_logo_bytes(self, tenant_id: uuid.UUID) -> tuple[bytes, str]:
        """Used only by the GET /company-profile/logo endpoint - raises
        LogoNotFoundError rather than tolerating a missing file the way
        get_document_context does, since an explicit logo request should
        surface a real 404 instead of silently rendering nothing."""
        profile = await self._repo.get_by_tenant(tenant_id)
        if profile is None or not profile.logo_storage_key or not profile.logo_content_type:
            raise LogoNotFoundError("This tenant has no logo")
        try:
            content = self._storage.load(profile.logo_storage_key)
        except DocumentNotFoundError as exc:
            # The DB row and the storage file can drift apart (storage
            # writes/deletes aren't transactional with the DB - a request
            # that rolls back after already touching storage is enough).
            # Self-heal here rather than leaving logo_url permanently
            # claiming a file that will never come back: clear the stale
            # reference so the next GET /company-profile honestly reports
            # no logo, and the uploader lets the tenant re-upload instead
            # of being stuck on a 404 forever.
            profile.logo_storage_key = None
            profile.logo_content_type = None
            profile.logo_uploaded_at = None
            await self._session.commit()
            raise LogoNotFoundError("The stored logo file is no longer available") from exc
        return content, profile.logo_content_type

    async def get_document_context(self, tenant_id: uuid.UUID) -> CompanyProfileDocumentContext:
        """The one cross-module entry point the 6 document-generating
        services and report export call - exactly one profile-row read
        plus (at most) one file read, never per line item. Never raises:
        a tenant with no profile row, or a profile whose logo file has
        drifted out of storage, both degrade to a document rendered
        without that piece rather than a failed generation."""
        profile = await self._repo.get_by_tenant(tenant_id)
        if profile is None:
            return CompanyProfileDocumentContext(
                display_name=None, tenant_details=None, logo_bytes=None, logo_content_type=None
            )

        display_name = profile.display_name or profile.legal_name
        tenant_details = _format_tenant_details(profile)
        logo_bytes: bytes | None = None
        if profile.logo_storage_key:
            try:
                logo_bytes = self._storage.load(profile.logo_storage_key)
            except (DocumentNotFoundError, InvalidStorageKeyError):
                logger.warning(
                    "company_profile_logo_missing",
                    tenant_id=str(tenant_id),
                    storage_key=profile.logo_storage_key,
                )
                logo_bytes = None

        return CompanyProfileDocumentContext(
            display_name=display_name,
            tenant_details=tenant_details,
            logo_bytes=logo_bytes,
            logo_content_type=profile.logo_content_type if logo_bytes else None,
        )

    async def _get_or_vivify(self, tenant_id: uuid.UUID) -> CompanyProfile:
        profile = await self._repo.get_by_tenant(tenant_id)
        if profile is not None:
            return profile

        tenant_name = await self._get_tenant_name(tenant_id)
        profile = CompanyProfile(tenant_id=tenant_id, legal_name=tenant_name)
        await self._repo.add(profile)
        try:
            await self._session.commit()
        except IntegrityError:
            # Two concurrent first-GETs for the same brand-new tenant
            # raced on the unique tenant_id index - the loser rolls back
            # and re-fetches the winner's row rather than erroring.
            await self._session.rollback()
            existing = await self._repo.get_by_tenant(tenant_id)
            if existing is None:
                raise
            return existing
        await self._session.refresh(profile)
        return profile

    async def _get_tenant_name(self, tenant_id: uuid.UUID) -> str:
        result = await self._session.execute(select(Tenant.name).where(Tenant.id == tenant_id))
        return result.scalar_one()

    @staticmethod
    def _to_response(profile: CompanyProfile) -> CompanyProfileResponse:
        return CompanyProfileResponse(
            id=profile.id,
            tenant_id=profile.tenant_id,
            legal_name=profile.legal_name,
            display_name=profile.display_name,
            company_code=profile.company_code,
            address_line1=profile.address_line1,
            address_line2=profile.address_line2,
            city=profile.city,
            state=profile.state,
            state_code=profile.state_code,
            pincode=profile.pincode,
            country=profile.country,
            phone=profile.phone,
            alt_phone=profile.alt_phone,
            email=profile.email,
            website=profile.website,
            gstin=profile.gstin,
            pan=profile.pan,
            logo_url=_LOGO_URL_PATH if profile.logo_storage_key else None,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
