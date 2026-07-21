from app.core.errors import ConflictError, NotFoundError


class BoatNotFoundError(NotFoundError):
    code = "BOAT_NOT_FOUND"


class DuplicateBoatCodeError(ConflictError):
    code = "DUPLICATE_BOAT_CODE"


class DuplicateBoatRegistrationNumberError(ConflictError):
    code = "DUPLICATE_BOAT_REGISTRATION_NUMBER"


class BoatCompanyNotFoundError(NotFoundError):
    """Raised when a boat's company_id doesn't reference an existing company."""

    code = "BOAT_COMPANY_NOT_FOUND"
