from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class DeliveryChallanNotFoundError(NotFoundError):
    code = "DELIVERY_CHALLAN_NOT_FOUND"


class DeliveryChallanItemNotFoundError(NotFoundError):
    code = "DELIVERY_CHALLAN_ITEM_NOT_FOUND"


class DeliveryChallanInvoiceNotFoundError(NotFoundError):
    """Raised when a delivery challan's invoice_id doesn't reference an
    existing invoice for the caller's tenant - also covers an invoice
    belonging to another tenant, which is indistinguishable from "does not
    exist" by design (InvoiceService.get is already tenant-scoped). Mirrors
    PurchaseBillPurchaseOrderNotFoundError."""

    code = "DELIVERY_CHALLAN_INVOICE_NOT_FOUND"


class DeliveryChallanInvoiceNotDeliverableError(BusinessRuleError):
    """Raised when a delivery challan is linked (at creation) to an invoice
    that is not ISSUED/PARTIALLY_PAID/PAID - a DRAFT invoice has no real
    customer commitment to deliver against yet, and a CANCELLED one never
    should. Mirrors PurchaseBillPurchaseOrderNotBillableError."""

    code = "DELIVERY_CHALLAN_INVOICE_NOT_DELIVERABLE"


class DeliveryChallanInvoiceItemNotFoundError(NotFoundError):
    """Raised when a delivery challan item's invoice_item_id does not belong
    to the delivery challan's own linked invoice - scoped by both invoice_id
    and tenant_id together, so an item belonging to a different invoice (or a
    different tenant) is indistinguishable from "does not exist". Mirrors
    PurchaseBillPurchaseOrderItemNotFoundError."""

    code = "DELIVERY_CHALLAN_INVOICE_ITEM_NOT_FOUND"


class DeliveryChallanNotDraftError(ConflictError):
    """Raised when trying to update, delete, or mutate items on a delivery
    challan that is no longer DRAFT. Mirrors PurchaseOrderNotDraftError."""

    code = "DELIVERY_CHALLAN_NOT_DRAFT"


class DeliveryChallanInvalidTransitionError(ConflictError):
    """Raised for a lifecycle transition attempted from a status that does
    not allow it - `dispatch` (only DRAFT), `deliver` (only DISPATCHED), and
    `cancel` (only DRAFT/DISPATCHED). Distinct from DeliveryChallanNotDraftError,
    which guards the DRAFT-only mutation boundary rather than a specific
    transition's precondition. Mirrors PurchaseOrderInvalidTransitionError."""

    code = "DELIVERY_CHALLAN_INVALID_TRANSITION"


class DeliveryChallanEmptyError(BusinessRuleError):
    """Raised when attempting to dispatch a delivery challan with zero items.
    Mirrors PurchaseOrderEmptyError."""

    code = "DELIVERY_CHALLAN_EMPTY"


class DeliveryChallanOverDeliveryError(BusinessRuleError):
    """Raised when a delivery challan item's quantity, added to every other
    valid (non-deleted, non-cancelled-challan) item already delivered against
    the same invoice item, would exceed that item's own invoiced quantity.
    Mirrors PurchaseBillOverBillingError."""

    code = "DELIVERY_CHALLAN_OVER_DELIVERY"


class DeliveryChallanNumberConflictError(ConflictError):
    """Defensive backstop for the `ix_delivery_challans_tenant_challan_number`
    unique index firing on commit - should be unreachable given
    DeliveryChallanService._allocate_challan_number's `SELECT ... FOR UPDATE`
    locking of the per-tenant/prefix/fiscal-year counter row, but documents
    intent if it ever does. Mirrors PurchaseOrderNumberConflictError."""

    code = "DELIVERY_CHALLAN_NUMBER_CONFLICT"


class DeliveryChallanDocumentNotAvailableError(BusinessRuleError):
    """Raised when GET /delivery-challans/{id}/document (Sprint 12 Session
    16) is requested for a delivery challan with no challan_number yet -
    numbers are assigned only at dispatch, never at draft creation, so a
    still-DRAFT challan has nothing to print. Also covers a challan
    cancelled directly from DRAFT (DeliveryChallanService.cancel allows
    DRAFT -> CANCELLED): such a challan never received a number either,
    unlike one cancelled from DISPATCHED, which keeps the number it was
    already assigned and can still be printed. Mirrors
    PurchaseOrderDocumentNotAvailableError exactly - same rule, same
    rationale, gated the same way (on the number, not the status)."""

    code = "DELIVERY_CHALLAN_DOCUMENT_NOT_AVAILABLE"


class DeliveryChallanCompanyNotFoundError(NotFoundError):
    """Raised when the linked invoice's own `company_id` doesn't resolve to
    an existing company for the caller's tenant while assembling a delivery
    challan's document context - defensive only (an invoice's billed
    company can't normally disappear), mirrors InvoiceCompanyNotFoundError."""

    code = "DELIVERY_CHALLAN_COMPANY_NOT_FOUND"


class DeliveryChallanFishNotFoundError(NotFoundError):
    """Raised when a referenced invoice item's own `fish_id` doesn't
    resolve to an existing fish while assembling a delivery challan's
    document context - defensive only, mirrors InvoiceItemFishNotFoundError."""

    code = "DELIVERY_CHALLAN_FISH_NOT_FOUND"
