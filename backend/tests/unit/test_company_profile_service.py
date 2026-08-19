"""Unit tests for app.modules.company_profile.service.CompanyProfileService
(Sprint 14: Company Profile & Organization Identity). Uses a `tmp_path`-
rooted LocalStorageService so logo file reads/writes never touch the real
configured storage root, mirroring test_documents_service.py's own
pattern."""

import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_engine.storage import LocalStorageService
from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import hash_password
from app.modules.company_profile.exceptions import (
    InvalidLogoContentTypeError,
    LogoNotFoundError,
    LogoTooLargeError,
)
from app.modules.company_profile.schemas import CompanyProfileUpsertRequest
from app.modules.company_profile.service import CompanyProfileService

# Minimal real, genuinely decodable images (generated via Pillow) -
# CompanyProfileService.upload_logo rejects anything build_logo_flowable
# can't decode (Sprint 14 Session 6 hardening: a Content-Type header
# alone was previously enough to pass validation, which let a corrupt/
# truncated "image" reach storage and later crash - not just degrade -
# every WeasyPrint report/statement PDF export for that tenant), so
# these fixtures need to actually decode, not just declare a content type.
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd4"
    "9a730000001349444154789c6364f8cfc0c0c0c004221818000c1e0103acd8"
    "8ba70000000049454e44ae426082"
)
_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb00430008060607060508"
    "0707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720"
    "222c231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909"
    "090c0b0c180d0d1832211c213232323232323232323232323232323232323232"
    "323232323232323232323232323232323232323232323232323232323232ffc0"
    "0011080002000203012200021101031101ffc4001f0000010501010101010100"
    "000000000000000102030405060708090a0bffc400b510000201030302040305"
    "0504040000017d01020300041105122131410613516107227114328191a10823"
    "42b1c11552d1f02433627282090a161718191a25262728292a3435363738393a"
    "434445464748494a535455565758595a636465666768696a737475767778797a"
    "838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7"
    "b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1"
    "f2f3f4f5f6f7f8f9faffc4001f01000301010101010101010100000000000001"
    "02030405060708090a0bffc400b5110002010204040304070504040001027700"
    "0102031104052131061241510761711322328108144291a1b1c109233352f015"
    "6272d10a162434e125f11718191a262728292a35363738393a43444546474849"
    "4a535455565758595a636465666768696a737475767778797a82838485868788"
    "898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4"
    "c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9"
    "faffda000c03010002110311003f00e2e8a28af993f713ffd9"
)


async def _make_tenant(db_session: AsyncSession, *, name: str = "Ocean Fresh") -> Tenant:
    tenant = Tenant(name=name, slug=f"profile-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.commit()
    return tenant


async def _make_user(db_session: AsyncSession, tenant_id: uuid.UUID) -> User:
    user = User(
        tenant_id=tenant_id,
        email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=f"user-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name="Test User",
        status=AccountStatus.ACTIVE,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _service(db_session: AsyncSession, tmp_path: Path) -> CompanyProfileService:
    return CompanyProfileService(db_session, storage=LocalStorageService(root=tmp_path))


class TestGetAutoVivify:
    async def test_first_get_creates_a_row_seeded_from_tenant_name(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session, name="Ocean Fresh Seafoods")
        service = _service(db_session, tmp_path)

        response = await service.get(tenant_id=tenant.id)

        assert response.legal_name == "Ocean Fresh Seafoods"
        assert response.tenant_id == tenant.id
        assert response.logo_url is None

    async def test_second_get_does_not_create_a_duplicate_row(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        service = _service(db_session, tmp_path)

        first = await service.get(tenant_id=tenant.id)
        second = await service.get(tenant_id=tenant.id)

        assert first.id == second.id


class TestTenantIsolation:
    async def test_two_tenants_get_independent_profiles(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant_a = await _make_tenant(db_session, name="Tenant A")
        tenant_b = await _make_tenant(db_session, name="Tenant B")
        service = _service(db_session, tmp_path)

        profile_a = await service.get(tenant_id=tenant_a.id)
        profile_b = await service.get(tenant_id=tenant_b.id)

        assert profile_a.id != profile_b.id
        assert profile_a.legal_name == "Tenant A"
        assert profile_b.legal_name == "Tenant B"

    async def test_get_or_none_returns_none_for_a_tenant_with_no_profile(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        service = _service(db_session, tmp_path)
        assert await service.get_or_none(tenant_id=uuid.uuid4()) is None


class TestUpsert:
    async def test_partial_update_only_changes_supplied_fields(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session, name="Original Name")
        actor = await _make_user(db_session, tenant.id)
        service = _service(db_session, tmp_path)
        await service.get(tenant_id=tenant.id)

        updated = await service.upsert(
            CompanyProfileUpsertRequest(city="Mumbai"),
            tenant_id=tenant.id,
            actor_id=actor.id,
        )
        assert updated.city == "Mumbai"
        assert updated.legal_name == "Original Name"

        further = await service.upsert(
            CompanyProfileUpsertRequest(gstin="27ABCDE1234F1Z5"),
            tenant_id=tenant.id,
            actor_id=actor.id,
        )
        assert further.gstin == "27ABCDE1234F1Z5"
        assert further.city == "Mumbai"

    async def test_upsert_on_a_brand_new_tenant_also_auto_vivifies(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session, name="Never Fetched Yet")
        actor = await _make_user(db_session, tenant.id)
        service = _service(db_session, tmp_path)

        updated = await service.upsert(
            CompanyProfileUpsertRequest(display_name="Trade Name"),
            tenant_id=tenant.id,
            actor_id=actor.id,
        )
        assert updated.legal_name == "Never Fetched Yet"
        assert updated.display_name == "Trade Name"


class TestUploadLogo:
    async def test_happy_path_upload_sets_logo_url(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        service = _service(db_session, tmp_path)

        response = await service.upload_logo(
            tenant.id, content=_PNG_BYTES, content_type="image/png"
        )
        assert response.logo_url == "/company-profile/logo"

        content, content_type = await service.load_logo_bytes(tenant.id)
        assert content == _PNG_BYTES
        assert content_type == "image/png"

    async def test_invalid_content_type_is_rejected(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        service = _service(db_session, tmp_path)

        with pytest.raises(InvalidLogoContentTypeError):
            await service.upload_logo(tenant.id, content=b"not-an-image", content_type="text/plain")

    async def test_oversized_logo_is_rejected(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        service = _service(db_session, tmp_path)

        from app.modules.company_profile.constants import MAX_LOGO_SIZE_BYTES

        oversized = b"\x00" * (MAX_LOGO_SIZE_BYTES + 1)
        with pytest.raises(LogoTooLargeError):
            await service.upload_logo(tenant.id, content=oversized, content_type="image/png")

    async def test_replacing_with_a_different_extension_deletes_the_old_key(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        storage = LocalStorageService(root=tmp_path)
        service = CompanyProfileService(db_session, storage=storage)

        await service.upload_logo(tenant.id, content=_PNG_BYTES, content_type="image/png")
        old_key = f"{tenant.id}/company-profile/logo.png"
        assert storage.exists(old_key)

        await service.upload_logo(tenant.id, content=_JPEG_BYTES, content_type="image/jpeg")
        new_key = f"{tenant.id}/company-profile/logo.jpg"
        assert storage.exists(new_key)
        assert not storage.exists(old_key)


class TestLoadLogoBytes:
    async def test_a_file_missing_from_storage_self_heals_the_stale_db_reference(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """Regression guard: storage writes/deletes aren't transactional
        with the DB (a request that touches storage then rolls back is
        enough to desync them - this exact drift shipped to a real
        tenant's row once already). A GET that finds the DB row pointing
        at a file that no longer exists must not just 404 - it must also
        clear the stale reference, so the tenant isn't stuck reporting a
        logo that will never come back."""
        tenant = await _make_tenant(db_session)
        storage = LocalStorageService(root=tmp_path)
        service = CompanyProfileService(db_session, storage=storage)
        await service.upload_logo(tenant.id, content=_PNG_BYTES, content_type="image/png")

        storage.delete(f"{tenant.id}/company-profile/logo.png")

        with pytest.raises(LogoNotFoundError):
            await service.load_logo_bytes(tenant.id)

        profile = await service.get(tenant_id=tenant.id)
        assert profile.logo_url is None


class TestDeleteLogo:
    async def test_removes_the_file_and_clears_the_fields(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        service = _service(db_session, tmp_path)
        await service.upload_logo(tenant.id, content=_PNG_BYTES, content_type="image/png")

        await service.delete_logo(tenant.id)

        with pytest.raises(LogoNotFoundError):
            await service.load_logo_bytes(tenant.id)

    async def test_deleting_when_absent_raises_not_found(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        service = _service(db_session, tmp_path)
        await service.get(tenant_id=tenant.id)

        with pytest.raises(LogoNotFoundError):
            await service.delete_logo(tenant.id)


class TestGetDocumentContext:
    async def test_returns_all_none_for_a_tenant_with_no_profile_row(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        service = _service(db_session, tmp_path)
        context = await service.get_document_context(uuid.uuid4())
        assert context.tenant_details is None
        assert context.logo_bytes is None
        assert context.logo_content_type is None

    async def test_returns_formatted_details_and_logo_bytes_when_populated(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        actor = await _make_user(db_session, tenant.id)
        service = _service(db_session, tmp_path)
        await service.upsert(
            CompanyProfileUpsertRequest(
                address_line1="12 Harbour Road",
                city="Mumbai",
                gstin="27ABCDE1234F1Z5",
            ),
            tenant_id=tenant.id,
            actor_id=actor.id,
        )
        await service.upload_logo(tenant.id, content=_PNG_BYTES, content_type="image/png")

        context = await service.get_document_context(tenant.id)

        assert context.tenant_details is not None
        assert "12 Harbour Road" in context.tenant_details
        assert "GSTIN: 27ABCDE1234F1Z5" in context.tenant_details
        assert context.logo_bytes == _PNG_BYTES
        assert context.logo_content_type == "image/png"

    async def test_missing_logo_file_on_disk_degrades_gracefully(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        tenant = await _make_tenant(db_session)
        storage = LocalStorageService(root=tmp_path)
        service = CompanyProfileService(db_session, storage=storage)
        await service.upload_logo(tenant.id, content=_PNG_BYTES, content_type="image/png")

        # Simulate the file drifting out of storage without the DB row
        # knowing - get_document_context must not raise.
        storage.delete(f"{tenant.id}/company-profile/logo.png")

        context = await service.get_document_context(tenant.id)
        assert context.logo_bytes is None
