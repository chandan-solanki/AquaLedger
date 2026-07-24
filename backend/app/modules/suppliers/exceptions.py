from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class SupplierNotFoundError(NotFoundError):
    code = "SUPPLIER_NOT_FOUND"


class DuplicateSupplierCodeError(ConflictError):
    code = "DUPLICATE_SUPPLIER_CODE"


class DuplicateSupplierNameError(ConflictError):
    code = "DUPLICATE_SUPPLIER_NAME"


class SupplierOutstandingCalculationError(BusinessRuleError):
    """Raised when the outstanding engine
    (app.modules.supplier_payments.domain.reconciliation.calculate_supplier_outstanding)
    computes a negative outstanding_amount for a supplier. Defense in depth,
    not a normal user-facing validation path: it is a SUM of
    purchase_bills.balance_amount, which PurchaseService's own reconciliation
    guard never lets go negative before this is ever called."""

    code = "SUPPLIER_OUTSTANDING_CALCULATION_ERROR"
