from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class PurchaseOrderNotFoundError(NotFoundError):
    code = "PURCHASE_ORDER_NOT_FOUND"


class PurchaseOrderItemNotFoundError(NotFoundError):
    code = "PURCHASE_ORDER_ITEM_NOT_FOUND"


class PurchaseOrderSupplierNotFoundError(NotFoundError):
    """Raised when a purchase order's supplier_id doesn't reference an
    existing supplier for the caller's tenant - also covers a supplier
    belonging to another tenant, which is indistinguishable from "does not
    exist" by design. Mirrors PurchaseBillSupplierNotFoundError."""

    code = "PURCHASE_ORDER_SUPPLIER_NOT_FOUND"


class PurchaseOrderSupplierInactiveError(BusinessRuleError):
    """Raised when a purchase order's supplier_id references a supplier that
    exists but is not ACTIVE. Mirrors PurchaseBillSupplierInactiveError -
    scoped to this module's own PURCHASE_ORDER_* code rather than reusing a
    generic company/supplier-inactive error."""

    code = "PURCHASE_ORDER_SUPPLIER_INACTIVE"


class PurchaseOrderNotDraftError(ConflictError):
    """Raised when trying to update, delete, mutate items on, or confirm a
    purchase order that is no longer DRAFT - a state-machine violation, same
    category as PurchaseBillNotDraftError. Enforced from the start so a
    draft can never be edited/deleted/confirmed out from under a
    confirmed/fulfilled/cancelled state."""

    code = "PURCHASE_ORDER_NOT_DRAFT"


class PurchaseOrderInvalidTransitionError(ConflictError):
    """Raised for a lifecycle transition attempted from a status that does
    not allow it - specifically `cancel` (only DRAFT/CONFIRMED may be
    cancelled) and `fulfill` (only CONFIRMED may be fulfilled). Distinct
    from PurchaseOrderNotDraftError, which guards the DRAFT-only mutation
    boundary rather than a specific transition's precondition."""

    code = "PURCHASE_ORDER_INVALID_TRANSITION"


class PurchaseOrderCalculationError(BusinessRuleError):
    """Raised when the financial engine
    (app.modules.purchase_orders.domain.totals) rejects a computed total -
    negative or exceeding what a NUMERIC(14,2) column can store. Defense in
    depth, not a normal user-facing validation path, mirroring
    PurchaseCalculationError: the request schemas already keep every input
    within the range that makes this unreachable except via extreme
    quantity x rate overflow."""

    code = "PURCHASE_ORDER_CALCULATION_ERROR"


class PurchaseOrderEmptyError(BusinessRuleError):
    """Raised when attempting to confirm a purchase order with zero items.
    Mirrors PurchaseBillEmptyError."""

    code = "PURCHASE_ORDER_EMPTY"


class PurchaseOrderTotalsInvalidError(BusinessRuleError):
    """Raised when the final pre-confirm recalculation
    (PurchaseOrderService._recalculate_purchase_order) rejects a computed
    total - negative or exceeding what a NUMERIC(14,2) column can store.
    Distinct from PurchaseOrderCalculationError (the same underlying
    FinancialCalculationError, raised during ordinary item add/update/
    delete) so a failure specifically at confirmation time carries its own
    code, mirroring PurchaseTotalsInvalidError."""

    code = "PURCHASE_ORDER_TOTALS_INVALID"


class PurchaseOrderDocumentNotAvailableError(BusinessRuleError):
    """Raised when GET /purchase-orders/{id}/document (Sprint 12 Session 11)
    is requested for a purchase order with no po_number yet - numbers are
    assigned only at confirmation, never at draft creation, so a still-DRAFT
    order has nothing to print. Also covers an order cancelled directly from
    DRAFT (PurchaseOrderService.cancel allows DRAFT -> CANCELLED): such an
    order never received a number either, unlike a cancel from CONFIRMED,
    which keeps the number it was already assigned and can still be printed.
    Mirrors PurchaseBillDocumentNotAvailableError."""

    code = "PURCHASE_ORDER_DOCUMENT_NOT_AVAILABLE"


class PurchaseOrderNumberConflictError(ConflictError):
    """Defensive backstop for the `ix_purchase_orders_tenant_po_number`
    unique index firing on commit - should be unreachable given
    PurchaseOrderService._allocate_purchase_order_number's `SELECT ... FOR
    UPDATE` locking of the per-tenant/prefix/fiscal-year counter row, but
    documents intent if it ever does, mirroring PurchaseNumberConflictError's
    posture."""

    code = "PURCHASE_ORDER_NUMBER_CONFLICT"
