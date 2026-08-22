from app.core.errors import NotFoundError, ValidationError


class InvalidAvatarContentTypeError(ValidationError):
    status_code = 415
    code = "INVALID_AVATAR_CONTENT_TYPE"


class AvatarTooLargeError(ValidationError):
    status_code = 413
    code = "AVATAR_TOO_LARGE"


class AvatarNotFoundError(NotFoundError):
    code = "AVATAR_NOT_FOUND"
