from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class InvoiceNotFoundError(NotFoundError):
    code = "INVOICE_NOT_FOUND"


class InvoiceItemNotFoundError(NotFoundError):
    code = "INVOICE_ITEM_NOT_FOUND"


class InvoiceCompanyNotFoundError(NotFoundError):
    """Raised when an invoice's company_id doesn't reference an existing
    company for the caller's tenant - also covers a company belonging to
    another tenant, which is indistinguishable from "does not exist" by
    design."""

    code = "INVOICE_COMPANY_NOT_FOUND"


class InvoiceCompanyInactiveError(BusinessRuleError):
    code = "INVOICE_COMPANY_INACTIVE"


class InvoiceNotDraftError(ConflictError):
    """Raised when trying to update or delete an invoice (or one of its
    items) that is no longer DRAFT - a state-machine violation, same
    category as reassigning the boat of a returned trip (see
    TripBoatChangeNotAllowedError and ConflictError's docstring in
    app.core.errors)."""

    code = "INVOICE_NOT_DRAFT"


class InvoiceItemTripCatchNotFoundError(NotFoundError):
    """Raised when an invoice item's trip_catch_id doesn't reference an
    existing trip catch for the caller's tenant - also covers a trip catch
    belonging to another tenant, which is indistinguishable from "does not
    exist" by design."""

    code = "INVOICE_ITEM_TRIP_CATCH_NOT_FOUND"


class InvoiceItemFishNotFoundError(NotFoundError):
    """Raised when an invoice item's fish_id doesn't reference an existing
    fish for the caller's tenant."""

    code = "INVOICE_ITEM_FISH_NOT_FOUND"


class InvoiceItemFishMismatchError(BusinessRuleError):
    """Raised when an invoice item's fish_id does not match the fish_id of
    its referenced trip_catch - a line can only sell the fish that was
    actually landed on that catch."""

    code = "INVOICE_ITEM_FISH_MISMATCH"


class InvoiceItemQuantityExceedsAvailableError(BusinessRuleError):
    """Raised when an invoice item's quantity exceeds the referenced trip
    catch's available_quantity. Validation only - Session 3 never deducts or
    reserves inventory; that happens only in the Session 5 issue workflow."""

    code = "INVOICE_ITEM_QUANTITY_EXCEEDS_AVAILABLE"


class InvoiceCalculationError(BusinessRuleError):
    """Raised when the financial engine
    (app.modules.invoices.domain.totals) rejects a computed total - negative
    or exceeding what a NUMERIC(14,2) column can store. Defense in depth,
    not a normal user-facing validation path: the request schemas already
    keep every input within the range that makes this unreachable except
    via extreme quantity x rate overflow."""

    code = "INVOICE_CALCULATION_ERROR"


class InvoiceEmptyError(BusinessRuleError):
    """Raised when attempting to issue an invoice with zero active line
    items (TASKS.md Session 5: "Must contain at least one item")."""

    code = "INVOICE_EMPTY"


class InvoiceInsufficientInventoryError(BusinessRuleError):
    """Raised during issue when an item's quantity exceeds its trip catch's
    currently available_quantity, revalidated under a `SELECT ... FOR
    UPDATE` lock immediately before deduction (ARCHITECTURE.md §13.3).

    Distinct from InvoiceItemQuantityExceedsAvailableError, which is the
    same check at item add/update time: that one runs against an unlocked
    read and can go stale (another invoice may be issued against the same
    trip catch in the meantime), so issue must re-check under lock and
    reports the failure with its own code."""

    code = "INVOICE_INSUFFICIENT_INVENTORY"


class InvoiceReconciliationError(BusinessRuleError):
    """Raised when the outstanding engine
    (app.modules.payments.domain.reconciliation.calculate_invoice_payment)
    rejects a recalculated paid_amount/balance_amount, or the invoice's
    current status is outside the payment lifecycle (draft/cancelled).
    Defense in depth, not a normal user-facing validation path:
    PaymentService's allocation ceilings (Session 3) and the "must be
    issued or partially paid" allocation guard already keep this
    unreachable in normal use, the same posture InvoiceCalculationError
    takes for the item-totals engine."""

    code = "INVOICE_RECONCILIATION_ERROR"


class InvoiceNumberConflictError(ConflictError):
    """Defensive backstop for the `ix_invoices_tenant_invoice_number` unique
    index firing on commit - should be unreachable given
    InvoiceService._allocate_invoice_number's `SELECT ... FOR UPDATE`
    locking of the per-tenant/prefix/fiscal-year counter row, but documents
    intent if it ever does (e.g. manual DB tampering), the same defensive
    posture every other module's _translate_integrity_error takes for its
    own unique constraints."""

    code = "INVOICE_NUMBER_CONFLICT"
