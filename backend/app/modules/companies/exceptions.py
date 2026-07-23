from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class CompanyNotFoundError(NotFoundError):
    code = "COMPANY_NOT_FOUND"


class DuplicateCompanyCodeError(ConflictError):
    code = "DUPLICATE_COMPANY_CODE"


class DuplicateCompanyNameError(ConflictError):
    code = "DUPLICATE_COMPANY_NAME"


class CompanyOutstandingCalculationError(BusinessRuleError):
    """Raised when the outstanding engine
    (app.modules.payments.domain.reconciliation.calculate_company_outstanding)
    computes a negative outstanding_amount for a company. Defense in depth,
    not a normal user-facing validation path: it is a SUM of
    invoices.balance_amount, which InvoiceService's own reconciliation guard
    never lets go negative before this is ever called."""

    code = "COMPANY_OUTSTANDING_CALCULATION_ERROR"
