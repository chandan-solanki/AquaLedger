from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class PurchaseBillNotFoundError(NotFoundError):
    code = "PURCHASE_BILL_NOT_FOUND"


class PurchaseBillItemNotFoundError(NotFoundError):
    code = "PURCHASE_BILL_ITEM_NOT_FOUND"


class PurchaseBillSupplierNotFoundError(NotFoundError):
    """Raised when a purchase bill's supplier_id doesn't reference an
    existing supplier for the caller's tenant - also covers a supplier
    belonging to another tenant, which is indistinguishable from "does not
    exist" by design. Mirrors InvoiceCompanyNotFoundError."""

    code = "PURCHASE_BILL_SUPPLIER_NOT_FOUND"


class PurchaseBillSupplierInactiveError(BusinessRuleError):
    """Raised when a purchase bill's supplier_id references a supplier that
    exists but is not ACTIVE. TASKS.md Sprint 11 Session 2 names this
    "SupplierInactive"; scoped to this module's own PURCHASE_BILL_* code
    the same way PaymentCompanyInactiveError is scoped rather than reusing
    CompanyNotFoundError/a generic company-inactive error - the caller is
    the purchase bill, not the supplier's own CRUD path."""

    code = "PURCHASE_BILL_SUPPLIER_INACTIVE"


class PurchaseBillNotDraftError(ConflictError):
    """Raised when trying to update or delete a purchase bill that is no
    longer DRAFT - a state-machine violation, same category as
    InvoiceNotDraftError/PaymentNotDraftError. Purchase bills only reach a
    non-DRAFT status starting with the Session 5 posting workflow, but the
    guard is enforced here from Session 2 on so a bill can never be edited/
    deleted out from under a future posted/cancelled state."""

    code = "PURCHASE_BILL_NOT_DRAFT"


class PurchaseCalculationError(BusinessRuleError):
    """Raised when the financial engine
    (app.modules.purchase.domain.totals) rejects a computed total - negative
    or exceeding what a NUMERIC(14,2) column can store. Defense in depth,
    not a normal user-facing validation path, mirroring
    InvoiceCalculationError: the request schemas already keep every input
    within the range that makes this unreachable except via extreme
    quantity x rate overflow."""

    code = "PURCHASE_CALCULATION_ERROR"


class PurchaseBillEmptyError(BusinessRuleError):
    """Raised when attempting to post a purchase bill with zero items
    (TASKS.md Session 5: "Must contain at least one item"). Mirrors
    InvoiceEmptyError."""

    code = "PURCHASE_BILL_EMPTY"


class PurchaseTotalsInvalidError(BusinessRuleError):
    """Raised when the final pre-post recalculation
    (PurchaseService._recalculate_purchase_bill, via
    app.modules.purchase.domain.totals) rejects a computed total - negative
    or exceeding what a NUMERIC(14,2) column can store. Distinct from
    PurchaseCalculationError (the same underlying
    FinancialCalculationError, raised during ordinary item add/update/
    delete) so a failure specifically at posting time - TASKS.md Session
    5's explicit "Validate totals: No negative values, No overflow" step -
    carries its own code."""

    code = "PURCHASE_TOTALS_INVALID"


class PurchaseBillReconciliationError(BusinessRuleError):
    """Raised when the outstanding engine
    (app.modules.supplier_payments.domain.reconciliation.calculate_purchase_bill_payment)
    rejects a recalculated paid_amount/balance_amount, or the purchase bill's
    current status is outside the payment lifecycle (draft/cancelled).
    Defense in depth, not a normal user-facing validation path:
    SupplierPaymentService's allocation ceilings (Session 3) and the "must be
    posted or partially paid" allocation guard already keep this unreachable
    in normal use, the same posture PurchaseCalculationError takes for the
    item-totals engine."""

    code = "PURCHASE_BILL_RECONCILIATION_ERROR"


class PurchaseBillDocumentNotAvailableError(BusinessRuleError):
    """Raised when GET /purchase/{id}/document (Sprint 12 Session 3) is
    requested for a purchase bill with no bill_number yet - a formal
    document can't carry a number that doesn't exist (numbers are
    assigned only at posting, never at draft creation), so a still-DRAFT
    bill has nothing to print. Mirrors InvoiceDocumentNotAvailableError."""

    code = "PURCHASE_BILL_DOCUMENT_NOT_AVAILABLE"


class PurchaseBillPurchaseOrderNotFoundError(NotFoundError):
    """Raised when a purchase bill's purchase_order_id doesn't reference an
    existing purchase order for the caller's tenant (Sprint 12 Session 12) -
    also covers a purchase order belonging to another tenant, which is
    indistinguishable from "does not exist" by design, mirroring
    PurchaseBillSupplierNotFoundError."""

    code = "PURCHASE_BILL_PURCHASE_ORDER_NOT_FOUND"


class PurchaseBillPurchaseOrderNotBillableError(BusinessRuleError):
    """Raised when a purchase bill tries to link a purchase order that is
    not CONFIRMED or FULFILLED - a DRAFT order has no commitment to bill
    against yet, and a CANCELLED order never should be. Mirrors
    PurchaseBillSupplierInactiveError's posture."""

    code = "PURCHASE_BILL_PURCHASE_ORDER_NOT_BILLABLE"


class PurchaseBillSupplierMismatchError(BusinessRuleError):
    """Raised when a purchase bill's supplier_id differs from the linked
    purchase order's own supplier_id - a bill can only be billed against a
    PO from the same supplier it is itself for."""

    code = "PURCHASE_BILL_SUPPLIER_MISMATCH"


class PurchaseBillNotLinkedToPurchaseOrderError(BusinessRuleError):
    """Raised when a purchase bill item specifies purchase_order_item_id
    but the bill itself has no purchase_order_id - an item can only
    reference a specific purchase order item once the bill as a whole is
    linked to that purchase order. purchase_order_id is set once, at bill
    creation, and is never changed afterward (PurchaseBillUpdateRequest has
    no field for it), so this is only ever reachable for a bill that was
    created without a purchase_order_id in the first place."""

    code = "PURCHASE_BILL_NOT_LINKED_TO_PURCHASE_ORDER"


class PurchaseBillPurchaseOrderItemNotFoundError(NotFoundError):
    """Raised when a purchase bill item's purchase_order_item_id doesn't
    reference an item that actually belongs to the bill's own linked
    purchase order (translated from PurchaseOrderItemNotFoundError, which
    is scoped by both purchase_order_id and item_id together - an item
    belonging to a different order is indistinguishable from "does not
    exist" here, the same way a foreign-tenant row is elsewhere)."""

    code = "PURCHASE_BILL_PURCHASE_ORDER_ITEM_NOT_FOUND"


class PurchaseBillOverBillingError(BusinessRuleError):
    """Raised when a purchase bill item's quantity, added to every other
    valid (non-deleted, non-cancelled-bill) bill item already billed
    against the same purchase order item, would exceed that item's own
    ordered quantity. The one hard-enforced constraint of the PO billing
    feature - always quantity-based, never trusting the frontend."""

    code = "PURCHASE_BILL_OVER_BILLING"


class PurchaseNumberConflictError(ConflictError):
    """Defensive backstop for the `ix_purchase_bills_tenant_bill_number`
    unique index firing on commit - should be unreachable given
    PurchaseService._allocate_purchase_number's `SELECT ... FOR UPDATE`
    locking of the per-tenant/prefix/fiscal-year counter row, but documents
    intent if it ever does (e.g. manual DB tampering), mirroring
    InvoiceNumberConflictError/PaymentNumberConflictError's posture."""

    code = "PURCHASE_NUMBER_CONFLICT"
