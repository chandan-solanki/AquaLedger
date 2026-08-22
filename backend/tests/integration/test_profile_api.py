import uuid

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.constants import AccountStatus
from app.modules.auth.models import AuditLog, Tenant, User
from app.modules.auth.security import create_access_token, hash_password

SUPER_ADMIN_EMAIL = "admin@fisherp.local"
SUPER_ADMIN_PASSWORD = "Admin@123"

# A minimal real 2x2 PNG (generated via Pillow) - genuinely decodable, not
# just a valid-looking header. Same reasoning as
# tests/integration/test_company_profile_api.py's own fixture: the upload
# path actually decodes this via ImageReader.getRGBData()
# (app.core.document_engine.reportlab_support.build_logo_flowable), so a
# header-only-valid/truncated fixture would silently pass validation here
# but corrupt real storage the first time some other test's (or a manually
# tested user's) same deterministic storage key was overwritten.
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd4"
    "9a730000001349444154789c6364f8cfc0c0c0c004221818000c1e0103acd8"
    "8ba70000000049454e44ae426082"
)

# A minimal real 2x2 JPEG (generated via Pillow) - used to test avatar
# replacement with a different content-type/extension, which exercises the
# "delete the old storage key" branch a same-format re-upload doesn't.
_JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605"
    "080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c202426"
    "2e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffdb00"
    "43010909090c0b0c180d0d1832211c213232323232323232323232323232"
    "32323232323232323232323232323232323232323232323232323232323232"
    "323232323232ffc00011080002000203012200021101031101ffc4001f0000"
    "010501010101010101000000000000000102030405060708090a0bffc400b5"
    "100002010303020403050504040000017d01020300041105122131410613"
    "51610722711432819"
    "1a1082342b1c11552d1f02433627282090a161718191a25262728292a34353"
    "6373839"
    "3a434445464748494a535455565758595a636465666768696a7374757677"
    "78797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b"
    "3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5"
    "e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffc4001f0100030101010101010101"
    "010000000000000102030405060708090a0bffc400b511000201020404030"
    "4070504040001027700010203110405213106124151076171132232810814"
    "4291a1b1c109233352f0156272d10a162434e125f11718191a262728292a3"
    "536373839"
    "3a434445464748494a535455565758595a636465666768696a737475767778"
    "797a8283848586878889"
    "8a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4"
    "c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8"
    "f9faffda000c03010002110311003f00e7a8a28af24fd0cfffd9"
)


async def _login(
    client: AsyncClient, email: str = SUPER_ADMIN_EMAIL, password: str = SUPER_ADMIN_PASSWORD
) -> Response:
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    response = await _login(client)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _admin_tenant_id(client: AsyncClient) -> uuid.UUID:
    response = await _login(client)
    return uuid.UUID(response.json()["user"]["tenant_id"])


async def _make_user(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    full_name: str = "Test User",
    username: str | None = None,
) -> User:
    user = User(
        tenant_id=tenant_id,
        email=f"user-{uuid.uuid4().hex[:8]}@fisherp.local",
        username=username or f"user-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("Whatever@123"),
        full_name=full_name,
        status=AccountStatus.ACTIVE,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _headers_for(user: User) -> dict[str, str]:
    token = create_access_token(subject=user.id, tenant_id=user.tenant_id, roles=[], permissions=[])
    return {"Authorization": f"Bearer {token}"}


async def _fresh_tenant(db_session: AsyncSession, name: str) -> Tenant:
    tenant = Tenant(name=name, slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.commit()
    return tenant


class TestUpdateProfile:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.put("/api/v1/profile", json={"full_name": "New Name"})
        assert response.status_code == 401

    async def test_updates_full_name_and_phone_for_self(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            "/api/v1/profile",
            json={"full_name": "Updated Admin", "phone": "9876543210"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "Updated Admin"
        assert body["phone"] == "9876543210"
        assert body["email"] == SUPER_ADMIN_EMAIL  # unchanged - not editable here

        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.json()["full_name"] == "Updated Admin"

    async def test_partial_update_only_changes_supplied_fields(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        first = await client.put(
            "/api/v1/profile", json={"full_name": "Only Name"}, headers=headers
        )
        assert first.json()["full_name"] == "Only Name"

        second = await client.put("/api/v1/profile", json={"phone": "9999999999"}, headers=headers)
        assert second.json()["phone"] == "9999999999"
        assert second.json()["full_name"] == "Only Name"

    async def test_duplicate_username_is_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        taken = await _make_user(db_session, tenant_id, username="already-taken")
        mover = await _make_user(db_session, tenant_id)

        response = await client.put(
            "/api/v1/profile", json={"username": taken.username}, headers=_headers_for(mover)
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DUPLICATE_USERNAME"

    async def test_forbidden_fields_are_rejected_by_schema(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        for payload in (
            {"is_superuser": True},
            {"role_id": str(uuid.uuid4())},
            {"status": "inactive"},
            {"email": "new@fisherp.local"},
            {"id": str(uuid.uuid4())},
            {"tenant_id": str(uuid.uuid4())},
        ):
            response = await client.put("/api/v1/profile", json=payload, headers=headers)
            assert response.status_code == 422, payload

    async def test_privilege_escalation_attempt_does_not_change_the_account(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        tenant_id = await _admin_tenant_id(client)
        victim = await _make_user(db_session, tenant_id)

        await client.put(
            "/api/v1/profile",
            json={"full_name": "Still Just Me", "is_superuser": True},
            headers=headers,
        )
        # The whole request 422s (extra="forbid"), so nothing changed at all,
        # not even the accompanying legitimate field.
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.json()["full_name"] != "Still Just Me"

        result = await db_session.execute(select(User).where(User.id == victim.id))
        assert result.scalar_one().is_superuser is False

    async def test_no_password_hash_or_tokens_in_response(self, client: AsyncClient) -> None:
        headers = await _admin_headers(client)
        response = await client.put(
            "/api/v1/profile", json={"full_name": "Clean Response"}, headers=headers
        )
        body = response.json()
        assert "password_hash" not in body
        assert "password" not in body
        assert "access_token" not in body
        assert "refresh_token" not in body

    async def test_successful_update_creates_audit_diff(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _admin_headers(client)
        await client.put("/api/v1/profile", json={"full_name": "Audited Name"}, headers=headers)

        result = await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "profile_updated")
            .order_by(AuditLog.created_at.desc())
        )
        log = result.scalars().first()
        assert log is not None
        assert log.entity_type == "user"
        changes = log.changes
        assert changes is not None
        assert set(changes.keys()) == {"full_name"}
        full_name_change = changes["full_name"]
        assert isinstance(full_name_change, dict)
        assert full_name_change["new"] == "Audited Name"

    async def test_failed_update_creates_zero_audit_rows(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_id = await _admin_tenant_id(client)
        taken = await _make_user(db_session, tenant_id, username="taken-for-audit-test")
        mover = await _make_user(db_session, tenant_id)

        before = (
            (await db_session.execute(select(AuditLog).where(AuditLog.action == "profile_updated")))
            .scalars()
            .all()
        )

        response = await client.put(
            "/api/v1/profile", json={"username": taken.username}, headers=_headers_for(mover)
        )
        assert response.status_code == 409

        after = (
            (await db_session.execute(select(AuditLog).where(AuditLog.action == "profile_updated")))
            .scalars()
            .all()
        )
        assert len(after) == len(before)


class TestAvatarUpload:
    """Every test that actually touches storage uses a throwaway user, never
    the shared seeded admin - the per-test DB rollback (tests/conftest.py's
    db_session fixture) does not undo filesystem writes, exactly the Sprint
    14 lesson tests/integration/test_company_profile_api.py already
    documents for the tenant logo. Reusing the admin account here would
    permanently overwrite/pollute real dev-environment avatar data across
    test runs."""

    async def test_upload_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/profile/avatar", files={"file": ("avatar.png", _PNG_BYTES, "image/png")}
        )
        assert response.status_code == 401

    async def test_valid_avatar_upload_and_download_round_trip(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Avatar Upload Co")
        user = await _make_user(db_session, tenant.id)
        headers = _headers_for(user)

        upload = await client.post(
            "/api/v1/profile/avatar",
            headers=headers,
            files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        )
        assert upload.status_code == 200
        assert upload.json()["avatar_url"] == "/profile/avatar"

        download = await client.get("/api/v1/profile/avatar", headers=headers)
        assert download.status_code == 200
        assert download.content == _PNG_BYTES
        assert download.headers["content-type"] == "image/png"
        assert "attachment" not in download.headers.get("content-disposition", "")

        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.json()["avatar_url"] == "/profile/avatar"

    async def test_avatar_replacement_succeeds(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Avatar Replace Co")
        user = await _make_user(db_session, tenant.id)
        headers = _headers_for(user)

        await client.post(
            "/api/v1/profile/avatar",
            headers=headers,
            files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        )
        replaced = await client.post(
            "/api/v1/profile/avatar",
            headers=headers,
            files={"file": ("avatar.jpg", _JPEG_BYTES, "image/jpeg")},
        )
        assert replaced.status_code == 200

        download = await client.get("/api/v1/profile/avatar", headers=headers)
        assert download.content == _JPEG_BYTES
        assert download.headers["content-type"] == "image/jpeg"

    async def test_invalid_content_type_is_415(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Bad Content Type Co")
        user = await _make_user(db_session, tenant.id)
        response = await client.post(
            "/api/v1/profile/avatar",
            headers=_headers_for(user),
            files={"file": ("avatar.txt", b"not-an-image", "text/plain")},
        )
        assert response.status_code == 415

    async def test_undecodable_bytes_with_a_valid_content_type_is_415(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Corrupt Upload Co")
        user = await _make_user(db_session, tenant.id)
        response = await client.post(
            "/api/v1/profile/avatar",
            headers=_headers_for(user),
            files={"file": ("avatar.png", b"not-actually-a-png", "image/png")},
        )
        assert response.status_code == 415

    async def test_oversized_avatar_is_413(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.modules.profile.constants import MAX_AVATAR_SIZE_BYTES

        tenant = await _fresh_tenant(db_session, "Oversized Avatar Co")
        user = await _make_user(db_session, tenant.id)
        oversized = b"\x00" * (MAX_AVATAR_SIZE_BYTES + 1)
        response = await client.post(
            "/api/v1/profile/avatar",
            headers=_headers_for(user),
            files={"file": ("avatar.png", oversized, "image/png")},
        )
        assert response.status_code == 413

    async def test_failed_replacement_preserves_existing_valid_avatar(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Preserve Avatar Co")
        user = await _make_user(db_session, tenant.id)
        headers = _headers_for(user)

        await client.post(
            "/api/v1/profile/avatar",
            headers=headers,
            files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        )
        corrupt = await client.post(
            "/api/v1/profile/avatar",
            headers=headers,
            files={"file": ("avatar.png", b"garbage-bytes", "image/png")},
        )
        assert corrupt.status_code == 415

        download = await client.get("/api/v1/profile/avatar", headers=headers)
        assert download.status_code == 200
        assert download.content == _PNG_BYTES

    async def test_failed_upload_creates_zero_audit_rows(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "No False Audit Co")
        user = await _make_user(db_session, tenant.id)

        before = (
            (await db_session.execute(select(AuditLog).where(AuditLog.action == "avatar_uploaded")))
            .scalars()
            .all()
        )

        response = await client.post(
            "/api/v1/profile/avatar",
            headers=_headers_for(user),
            files={"file": ("avatar.png", b"garbage-bytes", "image/png")},
        )
        assert response.status_code == 415

        after = (
            (await db_session.execute(select(AuditLog).where(AuditLog.action == "avatar_uploaded")))
            .scalars()
            .all()
        )
        assert len(after) == len(before)

    async def test_successful_upload_is_audited(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Audited Avatar Co")
        user = await _make_user(db_session, tenant.id)

        await client.post(
            "/api/v1/profile/avatar",
            headers=_headers_for(user),
            files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        )

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "avatar_uploaded", AuditLog.entity_id == user.id
            )
        )
        log = result.scalar_one()
        assert log.user_id == user.id
        assert log.changes is None  # no raw bytes/paths in the audit payload

    async def test_get_avatar_before_any_upload_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "No Avatar Yet Co")
        user = await _make_user(db_session, tenant.id)
        response = await client.get("/api/v1/profile/avatar", headers=_headers_for(user))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "AVATAR_NOT_FOUND"

    async def test_delete_avatar_succeeds_and_falls_back(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Delete Avatar Co")
        user = await _make_user(db_session, tenant.id)
        headers = _headers_for(user)

        await client.post(
            "/api/v1/profile/avatar",
            headers=headers,
            files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        )
        response = await client.delete("/api/v1/profile/avatar", headers=headers)
        assert response.status_code == 204

        after = await client.get("/api/v1/profile/avatar", headers=headers)
        assert after.status_code == 404

        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.json()["avatar_url"] is None

    async def test_deleting_when_absent_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Nothing To Delete Co")
        user = await _make_user(db_session, tenant.id)
        response = await client.delete("/api/v1/profile/avatar", headers=_headers_for(user))
        assert response.status_code == 404

    async def test_avatar_is_isolated_between_users(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await _fresh_tenant(db_session, "Avatar Owner Co")
        owner = await _make_user(db_session, tenant.id)
        other = await _make_user(db_session, tenant.id)

        await client.post(
            "/api/v1/profile/avatar",
            headers=_headers_for(owner),
            files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        )

        # `other` is a different user in the SAME tenant with no avatar of
        # their own - GET /profile/avatar has no id parameter at all, so
        # there is no path by which `other`'s request could ever resolve to
        # `owner`'s file.
        response = await client.get("/api/v1/profile/avatar", headers=_headers_for(other))
        assert response.status_code == 404

    async def test_avatar_is_tenant_isolated(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant_a = await _fresh_tenant(db_session, "Avatar Tenant A")
        tenant_b = await _fresh_tenant(db_session, "Avatar Tenant B")
        user_a = await _make_user(db_session, tenant_a.id)
        user_b = await _make_user(db_session, tenant_b.id)

        await client.post(
            "/api/v1/profile/avatar",
            headers=_headers_for(user_a),
            files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        )

        response = await client.get("/api/v1/profile/avatar", headers=_headers_for(user_b))
        assert response.status_code == 404
