from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class SupplierPaymentNotFoundError(NotFoundError):
    code = "SUPPLIER_PAYMENT_NOT_FOUND"


class SupplierPaymentAllocationNotFoundError(NotFoundError):
    code = "SUPPLIER_PAYMENT_ALLOCATION_NOT_FOUND"


class SupplierPaymentSupplierNotFoundError(NotFoundError):
    """Raised when a supplier payment's supplier_id doesn't reference an
    existing supplier for the caller's tenant - also covers a supplier
    belonging to another tenant, which is indistinguishable from "does not
    exist" by design. Mirrors PaymentCompanyNotFoundError/
    PurchaseBillSupplierNotFoundError."""

    code = "SUPPLIER_PAYMENT_SUPPLIER_NOT_FOUND"


class SupplierPaymentSupplierInactiveError(BusinessRuleError):
    code = "SUPPLIER_PAYMENT_SUPPLIER_INACTIVE"


class SupplierPaymentNotDraftError(ConflictError):
    """Raised when trying to update or delete a supplier payment that is no
    longer DRAFT - a state-machine violation, same category as
    PaymentNotDraftError/PurchaseBillNotDraftError. Supplier payments only
    reach a non-DRAFT status starting with the Session 5 posting workflow,
    but the guard is enforced here from Session 2 on so a payment can never
    be edited/deleted out from under a future posted/cancelled state."""

    code = "SUPPLIER_PAYMENT_NOT_DRAFT"


class SupplierPaymentAllocationPurchaseBillNotFoundError(NotFoundError):
    """Raised when an allocation's purchase_bill_id doesn't reference an
    existing purchase bill for the caller's tenant - also covers a bill
    belonging to another tenant, which is indistinguishable from "does not
    exist" by design. Mirrors PaymentAllocationInvoiceNotFoundError."""

    code = "SUPPLIER_PAYMENT_ALLOCATION_PURCHASE_BILL_NOT_FOUND"


class SupplierPaymentAllocationPaymentNotDraftError(ConflictError):
    """Raised when trying to allocate, update or remove an allocation on a
    supplier payment that is no longer DRAFT - the allocation-specific
    counterpart of SupplierPaymentNotDraftError, kept as its own code so
    allocation endpoints report an allocation-scoped conflict rather than
    reusing the CRUD endpoints' generic one. Mirrors
    PaymentAllocationPaymentNotDraftError."""

    code = "SUPPLIER_PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"


class SupplierPaymentPurchaseBillNotAllocatableError(BusinessRuleError):
    """Raised when the referenced purchase bill's status isn't eligible to
    receive an allocation - currently only POSTED (TASKS.md Sprint 12
    Session 3: "Purchase Bill status POSTED, PARTIALLY_PAID"), but
    PARTIALLY_PAID isn't a reachable PurchaseBill status yet - it is
    introduced by the Session 4 outstanding-reconciliation engine, which
    this session deliberately does not implement (PurchaseBill.paid_amount/
    balance_amount/status are never written to here). Mirrors
    PaymentAllocationInvoiceInvalidStatusError."""

    code = "SUPPLIER_PAYMENT_PURCHASE_BILL_NOT_ALLOCATABLE"


class SupplierPaymentAllocationAmountExceededError(BusinessRuleError):
    """Raised when allocated_amount exceeds either ceiling TASKS.md Sprint
    12 Session 3 requires: the purchase bill's balance_amount, or the
    supplier payment's unallocated_amount. One shared code for both - the
    message (see
    app.modules.supplier_payments.domain.allocation.validate_allocation_amount)
    distinguishes which ceiling was hit. Mirrors
    PaymentAllocationAmountExceededError."""

    code = "SUPPLIER_PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"


class SupplierPaymentNoAllocationsError(BusinessRuleError):
    """Raised when trying to post a supplier payment with zero allocations
    (TASKS.md Sprint 12 Session 5: "Must contain at least one allocation").
    An unallocated payment is still on-account credit, not yet something to
    lock into a numbered financial record. Mirrors PaymentNoAllocationsError."""

    code = "SUPPLIER_PAYMENT_NO_ALLOCATIONS"


class SupplierPaymentTotalsInvalidError(BusinessRuleError):
    """Raised when a supplier payment's `allocated_amount +
    unallocated_amount != amount` immediately before posting (TASKS.md
    Sprint 12 Session 5's explicit step 5 verification). Defense in depth,
    not a normal user-facing validation path: post() recomputes both fields
    from the sum of active allocations one step earlier (the same
    recompute-from-source discipline every allocation mutation uses), which
    keeps this invariant true by construction - this check exists to fail
    loudly rather than silently post a corrupted row. Mirrors
    PaymentTotalsInvalidError."""

    code = "SUPPLIER_PAYMENT_TOTALS_INVALID"


class SupplierPaymentNumberConflictError(ConflictError):
    """Defensive backstop for the `ix_supplier_payments_tenant_payment_number`
    unique index firing on commit - should be unreachable given
    SupplierPaymentService._allocate_payment_number's `SELECT ... FOR
    UPDATE` locking of the per-tenant/prefix/fiscal-year counter row, but
    documents intent if it ever does, the same defensive posture
    PaymentNumberConflictError takes for payments."""

    code = "SUPPLIER_PAYMENT_NUMBER_CONFLICT"
