from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status

from app.common.request_context import build_request_context
from app.common.schemas import ErrorResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import UserProfileResponse
from app.modules.profile.constants import MAX_AVATAR_SIZE_BYTES
from app.modules.profile.dependencies import get_profile_service
from app.modules.profile.exceptions import AvatarTooLargeError, InvalidAvatarContentTypeError
from app.modules.profile.schemas import ProfileUpdateRequest
from app.modules.profile.service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
}
_AVATAR_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "The caller has no avatar"},
}
_AVATAR_UPLOAD_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    413: {"model": ErrorResponse, "description": "Avatar exceeds the maximum allowed size"},
    415: {"model": ErrorResponse, "description": "Unsupported avatar content type"},
}


@router.put(
    "",
    response_model=UserProfileResponse,
    summary="Update the current user's own profile",
    description=(
        "Partial update of the caller's OWN account only - full_name, username "
        "and phone. There is no id/tenant_id/email/role/status/is_superuser "
        "field on this request: those remain out of reach through this "
        "endpoint by construction, not by convention."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        409: {"model": ErrorResponse, "description": "Username already in use"},
    },
)
async def update_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileResponse:
    return await service.update_profile(current_user, payload, ctx=build_request_context(request))


@router.get(
    "/avatar",
    summary="Serve the current user's own avatar bytes",
    description=(
        "Streams the avatar image for inline display (e.g. <img src>) - no "
        "Content-Disposition: attachment. The caller is resolved from the "
        "authenticated session only; no id parameter exists on this route."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_AVATAR_NOT_FOUND_RESPONSE,
        200: {
            "description": "The avatar image bytes",
            "content": {"image/*": {"schema": {"type": "string", "format": "binary"}}},
        },
    },
)
async def get_avatar(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> Response:
    content, content_type = await service.load_avatar_bytes(current_user)
    # The route path is identical for every caller ("whoever is currently
    # authenticated"), so without an explicit no-store/private directive a
    # browser or intermediate cache has no signal that this response is
    # per-identity - on a shared/kiosk device, User A's avatar bytes could
    # otherwise be served back to User B from the browser's own HTTP cache
    # after a user switch in the same browser profile.
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post(
    "/avatar",
    response_model=UserProfileResponse,
    summary="Upload or replace the current user's own avatar",
    description=(
        f"Accepts PNG, JPEG or WebP up to {MAX_AVATAR_SIZE_BYTES} bytes. A "
        "re-upload replaces any existing avatar in place."
    ),
    responses={**_COMMON_ERROR_RESPONSES, **_AVATAR_UPLOAD_ERROR_RESPONSES},
)
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileResponse:
    # Never trust Content-Length/file.size alone - read one byte beyond the
    # cap so an over-limit upload is caught by the actual byte count, not a
    # client-declared (and possibly false) header.
    content = await file.read(MAX_AVATAR_SIZE_BYTES + 1)
    if len(content) > MAX_AVATAR_SIZE_BYTES:
        raise AvatarTooLargeError(
            f"Avatar exceeds the maximum size of {MAX_AVATAR_SIZE_BYTES} bytes"
        )
    if not file.content_type:
        raise InvalidAvatarContentTypeError("Missing content type")
    return await service.upload_avatar(
        current_user,
        content=content,
        content_type=file.content_type,
        ctx=build_request_context(request),
    )


@router.delete(
    "/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove the current user's own avatar",
    description="Deletes the stored file and clears the avatar fields.",
    responses={**_COMMON_ERROR_RESPONSES, **_AVATAR_NOT_FOUND_RESPONSE},
)
async def delete_avatar(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    await service.delete_avatar(current_user, ctx=build_request_context(request))
