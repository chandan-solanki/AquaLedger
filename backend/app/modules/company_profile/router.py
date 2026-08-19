from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.common.schemas import ErrorResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.company_profile.constants import MAX_LOGO_SIZE_BYTES
from app.modules.company_profile.dependencies import get_company_profile_service
from app.modules.company_profile.exceptions import InvalidLogoContentTypeError, LogoTooLargeError
from app.modules.company_profile.permissions import SETTINGS_MANAGE
from app.modules.company_profile.schemas import CompanyProfileResponse, CompanyProfileUpsertRequest
from app.modules.company_profile.service import CompanyProfileService

router = APIRouter(prefix="/company-profile", tags=["company-profile"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}
_LOGO_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "This tenant has no logo"},
}
_LOGO_UPLOAD_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    413: {"model": ErrorResponse, "description": "Logo exceeds the maximum allowed size"},
    415: {"model": ErrorResponse, "description": "Unsupported logo content type"},
}


@router.get(
    "",
    response_model=CompanyProfileResponse,
    summary="Get the current tenant's company profile",
    description=(
        "Returns the caller's own tenant profile - never another tenant's, and never "
        "404: a brand-new tenant's first GET auto-creates an empty profile seeded from "
        "the tenant's display name."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(SETTINGS_MANAGE))],
)
async def get_company_profile(
    current_user: User = Depends(get_current_user),
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> CompanyProfileResponse:
    return await service.get(tenant_id=current_user.tenant_id)


@router.put(
    "",
    response_model=CompanyProfileResponse,
    summary="Update the current tenant's company profile",
    description="Partial update: only fields present in the request body are changed.",
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(SETTINGS_MANAGE))],
)
async def update_company_profile(
    payload: CompanyProfileUpsertRequest,
    current_user: User = Depends(get_current_user),
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> CompanyProfileResponse:
    return await service.upsert(payload, tenant_id=current_user.tenant_id, actor_id=current_user.id)


@router.post(
    "/logo",
    response_model=CompanyProfileResponse,
    summary="Upload or replace the current tenant's logo",
    description=(
        f"Accepts PNG, JPEG or WebP up to {MAX_LOGO_SIZE_BYTES} bytes. A re-upload "
        "replaces any existing logo in place."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_LOGO_UPLOAD_ERROR_RESPONSES},
    dependencies=[Depends(require_permission(SETTINGS_MANAGE))],
)
async def upload_company_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> CompanyProfileResponse:
    # Never trust Content-Length/file.size alone - read one byte beyond
    # the cap so an over-limit upload is caught by the actual byte count,
    # not a client-declared (and possibly false) header.
    content = await file.read(MAX_LOGO_SIZE_BYTES + 1)
    if len(content) > MAX_LOGO_SIZE_BYTES:
        raise LogoTooLargeError(f"Logo exceeds the maximum size of {MAX_LOGO_SIZE_BYTES} bytes")
    if not file.content_type:
        raise InvalidLogoContentTypeError("Missing content type")
    return await service.upload_logo(
        current_user.tenant_id, content=content, content_type=file.content_type
    )


@router.get(
    "/logo",
    summary="Serve the current tenant's logo bytes",
    description=(
        "Streams the logo image for inline display (e.g. <img src>) - no "
        "Content-Disposition: attachment, unlike Document Center downloads. Tenant is "
        "resolved from the authenticated session only; the storage key never leaves "
        "the server."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_LOGO_NOT_FOUND_RESPONSE,
        200: {
            "description": "The logo image bytes",
            "content": {"image/*": {"schema": {"type": "string", "format": "binary"}}},
        },
    },
    dependencies=[Depends(require_permission(SETTINGS_MANAGE))],
)
async def get_company_logo(
    current_user: User = Depends(get_current_user),
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> Response:
    content, content_type = await service.load_logo_bytes(current_user.tenant_id)
    return Response(content=content, media_type=content_type)


@router.delete(
    "/logo",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove the current tenant's logo",
    description=(
        "Deletes the stored file and clears the logo fields. The company profile row "
        "itself is untouched."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_LOGO_NOT_FOUND_RESPONSE},
    dependencies=[Depends(require_permission(SETTINGS_MANAGE))],
)
async def delete_company_logo(
    current_user: User = Depends(get_current_user),
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> None:
    await service.delete_logo(current_user.tenant_id)
