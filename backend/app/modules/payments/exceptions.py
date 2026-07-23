from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class PaymentNotFoundError(NotFoundError):
    code = "PAYMENT_NOT_FOUND"


class PaymentAllocationNotFoundError(NotFoundError):
    code = "PAYMENT_ALLOCATION_NOT_FOUND"


class PaymentCompanyNotFoundError(NotFoundError):
    """Raised when a payment's company_id doesn't reference an existing
    company for the caller's tenant - also covers a company belonging to
    another tenant, which is indistinguishable from "does not exist" by
    design. Mirrors InvoiceCompanyNotFoundError."""

    code = "PAYMENT_COMPANY_NOT_FOUND"


class PaymentCompanyInactiveError(BusinessRuleError):
    code = "PAYMENT_COMPANY_INACTIVE"


class PaymentNotDraftError(ConflictError):
    """Raised when trying to update or delete a payment that is no longer
    DRAFT - a state-machine violation, same category as
    InvoiceNotDraftError. Payments only reach a non-DRAFT status starting
    with the Session 5 posting workflow, but the guard is enforced here from
    Session 2 on so a payment can never be edited/deleted out from under a
    future posted/cancelled state."""

    code = "PAYMENT_NOT_DRAFT"


class PaymentAllocationInvoiceNotFoundError(NotFoundError):
    """Raised when an allocation's invoice_id doesn't reference an existing
    invoice for the caller's tenant - also covers an invoice belonging to
    another tenant, which is indistinguishable from "does not exist" by
    design. Mirrors InvoiceCompanyNotFoundError."""

    code = "PAYMENT_ALLOCATION_INVOICE_NOT_FOUND"


class PaymentAllocationPaymentNotDraftError(ConflictError):
    """Raised when trying to allocate, update or remove an allocation on a
    payment that is no longer DRAFT - the allocation-specific counterpart of
    PaymentNotDraftError, kept as its own code so allocation endpoints
    report an allocation-scoped conflict rather than reusing the CRUD
    endpoints' generic one."""

    code = "PAYMENT_ALLOCATION_PAYMENT_NOT_DRAFT"


class PaymentAllocationInvoiceInvalidStatusError(BusinessRuleError):
    """Raised when the referenced invoice's status isn't ISSUED or
    PARTIALLY_PAID - a draft invoice has no balance to settle yet, and a
    cancelled or fully paid one has none left (TASKS.md Sprint 10 Session
    3: "Reject: DRAFT invoices, CANCELLED invoices, PAID invoices")."""

    code = "PAYMENT_ALLOCATION_INVOICE_INVALID_STATUS"


class PaymentAllocationAmountExceededError(BusinessRuleError):
    """Raised when allocated_amount exceeds either ceiling TASKS.md Sprint
    10 Session 3 requires: the invoice's balance_amount, or the payment's
    unallocated_amount. One shared code for both - the message (see
    app.modules.payments.domain.allocation.validate_allocation_amount)
    distinguishes which ceiling was hit."""

    code = "PAYMENT_ALLOCATION_AMOUNT_EXCEEDED"


class PaymentNoAllocationsError(BusinessRuleError):
    """Raised when trying to post a payment with zero allocations
    (TASKS.md Sprint 10 Session 5: "Payment must have at least one
    allocation"). An unallocated payment is still on-account credit, not
    yet something to lock into a numbered financial record."""

    code = "PAYMENT_NO_ALLOCATIONS"


class PaymentTotalsInvalidError(BusinessRuleError):
    """Raised when a payment's `allocated_amount + unallocated_amount !=
    amount` immediately before posting (TASKS.md Sprint 10 Session 5's
    explicit step 7 verification). Defense in depth, not a normal user-
    facing validation path: post() recomputes both fields from the sum of
    active allocations one step earlier (the same recompute-from-source
    discipline every allocation mutation uses), which keeps this invariant
    true by construction - this check exists to fail loudly rather than
    silently post a corrupted row, the same posture
    InvoiceCalculationError takes for its own engine."""

    code = "PAYMENT_TOTALS_INVALID"


class PaymentNumberConflictError(ConflictError):
    """Defensive backstop for the `ix_payments_tenant_payment_number`
    unique index firing on commit - should be unreachable given
    PaymentService._allocate_payment_number's `SELECT ... FOR UPDATE`
    locking of the per-tenant/prefix/fiscal-year counter row, but documents
    intent if it ever does, the same defensive posture
    InvoiceNumberConflictError takes for invoices."""

    code = "PAYMENT_NUMBER_CONFLICT"
