from app.core.errors import ConflictError, NotFoundError


class CompanyNotFoundError(NotFoundError):
    code = "COMPANY_NOT_FOUND"


class DuplicateCompanyCodeError(ConflictError):
    code = "DUPLICATE_COMPANY_CODE"


class DuplicateCompanyNameError(ConflictError):
    code = "DUPLICATE_COMPANY_NAME"
