import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# A minimal real 2x2 PNG (generated via Pillow) - genuinely decodable,
# not just a valid-looking header. Document generation actually decodes
# this via ImageReader.getRGBData() (app.core.document_engine.
# reportlab_support.build_logo_flowable), so a header-only-valid/
# truncated-IDAT fixture would silently corrupt the *real* configured
# storage root the first time this test's upload overwrote another
# test's (or a manually-tested tenant's) same deterministic storage key.
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd4"
    "9a730000001349444154789c6364f8cfc0c0c0c004221818000c1e0103acd8"
    "8ba70000000049454e44ae426082"
)


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _admin_tenant_id(client: AsyncClient) -> uuid.UUID:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD},
    )
    return uuid.UUID(response.json()["user"]["tenant_id"])


async def _make_user_headers(
    db_session: AsyncSession, tenant_id: uuid.UUID, permissions: list[str]
) -> dict[str, str]:
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
    token = create_access_token(
        subject=user.id, tenant_id=user.tenant_id, roles=["custom"], permissions=permissions
    )
    return {"Authorization": f"Bearer {token}"}


class TestGetCompanyProfile:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/company-profile")
        assert response.status_code == 401

    async def test_requires_settings_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.get("/api/v1/company-profile", headers=headers)
        assert response.status_code == 403

    async def test_first_get_auto_vivifies_and_never_404s(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # A fresh tenant, not the shared admin dev tenant - the admin
        # tenant's profile is genuine long-lived data (set up through the
        # actual UI across manual verification sessions), not a blank
        # slate this test can assume.
        tenant = Tenant(name="Fresh Co", slug=f"fresh-{uuid.uuid4().hex[:8]}")
        db_session.add(tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, tenant.id, ["settings:manage"])

        response = await client.get("/api/v1/company-profile", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["legal_name"] == "Fresh Co"
        assert body["logo_url"] is None

    async def test_second_get_returns_the_same_row(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        first = await client.get("/api/v1/company-profile", headers=headers)
        second = await client.get("/api/v1/company-profile", headers=headers)
        assert first.json()["id"] == second.json()["id"]

    async def test_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _admin_headers(client)
        own = await client.get("/api/v1/company-profile", headers=headers)

        other_tenant = Tenant(name="Other Co", slug=f"other-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, ["settings:manage"])

        other = await client.get("/api/v1/company-profile", headers=other_headers)
        assert other.json()["id"] != own.json()["id"]
        assert other.json()["legal_name"] == "Other Co"


class TestUpdateCompanyProfile:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put("/api/v1/company-profile", json={"city": "Mumbai"})
        assert response.status_code == 401

    async def test_requires_settings_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.put(
            "/api/v1/company-profile", json={"city": "Mumbai"}, headers=headers
        )
        assert response.status_code == 403

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        await client.get("/api/v1/company-profile", headers=headers)

        first = await client.put(
            "/api/v1/company-profile", json={"city": "Mumbai"}, headers=headers
        )
        assert first.status_code == 200
        assert first.json()["city"] == "Mumbai"

        second = await client.put(
            "/api/v1/company-profile", json={"gstin": "27ABCDE1234F1Z5"}, headers=headers
        )
        assert second.status_code == 200
        assert second.json()["gstin"] == "27ABCDE1234F1Z5"
        assert second.json()["city"] == "Mumbai"

    async def test_invalid_gstin_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            "/api/v1/company-profile", json={"gstin": "BADGSTIN"}, headers=headers
        )
        assert response.status_code == 422
        assert "gstin" in response.json()["error"]["field_errors"]

    async def test_invalid_pan_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            "/api/v1/company-profile", json={"pan": "NOTAPAN"}, headers=headers
        )
        assert response.status_code == 422
        assert "pan" in response.json()["error"]["field_errors"]

    async def test_blank_legal_name_is_422(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            "/api/v1/company-profile", json={"legal_name": ""}, headers=headers
        )
        assert response.status_code == 422


class TestCompanyLogo:
    async def test_upload_requires_settings_manage_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        headers = await _make_user_headers(db_session, tenant_id, [])
        response = await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.png", _PNG_BYTES, "image/png")},
        )
        assert response.status_code == 403

    async def test_upload_and_download_round_trip(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Fresh tenant, not the shared admin dev tenant: this upload writes
        # real bytes to disk, which the per-test DB rollback does not undo -
        # against the shared tenant it would permanently overwrite whatever
        # real logo a developer configured through the actual UI.
        tenant = Tenant(name="Upload Round Trip Co", slug=f"upload-rt-{uuid.uuid4().hex[:8]}")
        db_session.add(tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, tenant.id, ["settings:manage"])

        upload = await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.png", _PNG_BYTES, "image/png")},
        )
        assert upload.status_code == 200
        assert upload.json()["logo_url"] == "/company-profile/logo"

        download = await client.get("/api/v1/company-profile/logo", headers=headers)
        assert download.status_code == 200
        assert download.content == _PNG_BYTES
        assert download.headers["content-type"] == "image/png"
        assert "attachment" not in download.headers.get("content-disposition", "")

    async def test_invalid_content_type_is_415(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.txt", b"not-an-image", "text/plain")},
        )
        assert response.status_code == 415

    async def test_undecodable_bytes_with_a_valid_content_type_is_415(
        self, client: AsyncClient
    ) -> None:
        # Content-Type is a client-supplied header, not proof the bytes are
        # a real image - a corrupt/truncated file that merely claims to be
        # image/png must be rejected here, not accepted and only fail much
        # later when a PDF is generated from it.
        headers = await _admin_headers(client)
        response = await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.png", b"not-actually-a-png", "image/png")},
        )
        assert response.status_code == 415

    async def test_oversized_logo_is_413(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        from app.modules.company_profile.constants import MAX_LOGO_SIZE_BYTES

        oversized = b"\x00" * (MAX_LOGO_SIZE_BYTES + 1)
        response = await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.png", oversized, "image/png")},
        )
        assert response.status_code == 413

    async def test_get_logo_before_any_upload_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Fresh tenant - the shared admin dev tenant already has a real
        # logo configured through actual UI use, not a blank slate.
        tenant = Tenant(name="No Logo Yet Co", slug=f"no-logo-{uuid.uuid4().hex[:8]}")
        db_session.add(tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, tenant.id, ["settings:manage"])

        response = await client.get("/api/v1/company-profile/logo", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "LOGO_NOT_FOUND"

    async def test_delete_logo(self, client: AsyncClient, db_session: AsyncSession) -> None:
        # Fresh tenant, not the shared admin dev tenant: a real delete of
        # the shared tenant's logo file on disk survives this test's DB
        # rollback, permanently destroying whatever real logo a developer
        # configured through the actual UI.
        tenant = Tenant(name="Delete Logo Co", slug=f"delete-logo-{uuid.uuid4().hex[:8]}")
        db_session.add(tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, tenant.id, ["settings:manage"])

        await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.png", _PNG_BYTES, "image/png")},
        )
        response = await client.delete("/api/v1/company-profile/logo", headers=headers)
        assert response.status_code == 204

        after = await client.get("/api/v1/company-profile/logo", headers=headers)
        assert after.status_code == 404

    async def test_deleting_when_absent_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Fresh tenant - the shared admin dev tenant already has a real
        # logo configured through actual UI use, not a blank slate.
        tenant = Tenant(name="Nothing To Delete Co", slug=f"no-delete-{uuid.uuid4().hex[:8]}")
        db_session.add(tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, tenant.id, ["settings:manage"])

        response = await client.delete("/api/v1/company-profile/logo", headers=headers)
        assert response.status_code == 404

    async def test_logo_is_tenant_isolated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Fresh tenant for the uploader, not the shared admin dev tenant -
        # same reasoning as test_upload_and_download_round_trip: the write
        # survives this test's DB rollback.
        tenant = Tenant(name="Logo Owner Co", slug=f"logo-owner-{uuid.uuid4().hex[:8]}")
        db_session.add(tenant)
        await db_session.commit()
        headers = await _make_user_headers(db_session, tenant.id, ["settings:manage"])
        await client.post(
            "/api/v1/company-profile/logo",
            headers=headers,
            files={"file": ("logo.png", _PNG_BYTES, "image/png")},
        )

        other_tenant = Tenant(name="Logo Isolation Co", slug=f"logo-iso-{uuid.uuid4().hex[:8]}")
        db_session.add(other_tenant)
        await db_session.commit()
        other_headers = await _make_user_headers(db_session, other_tenant.id, ["settings:manage"])

        response = await client.get("/api/v1/company-profile/logo", headers=other_headers)
        assert response.status_code == 404
