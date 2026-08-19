from app.core.errors import NotFoundError, ValidationError


class CompanyProfileNotFoundError(NotFoundError):
    code = "COMPANY_PROFILE_NOT_FOUND"


class InvalidLogoContentTypeError(ValidationError):
    status_code = 415
    code = "INVALID_LOGO_CONTENT_TYPE"


class LogoTooLargeError(ValidationError):
    status_code = 413
    code = "LOGO_TOO_LARGE"


class LogoNotFoundError(NotFoundError):
    code = "LOGO_NOT_FOUND"
