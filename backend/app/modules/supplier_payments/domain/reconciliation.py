"""Sprint 12 Session 4 - the outstanding/reconciliation engine
(ARCHITECTURE.md §5.3's "never present a stored aggregate you cannot
re-derive on demand"), mirroring app.modules.payments.domain.reconciliation
exactly, on the buy side.

Pure domain logic: no SQLAlchemy, no FastAPI, no I/O (ARCHITECTURE.md §1.3's
Domain Layer). Money math is Decimal-only throughout, ROUND_HALF_UP to 2
decimal places - the same discipline purchase/domain/totals.py and
supplier_payments/domain/allocation.py apply to their own calculations.

Holds every financial calculation the outstanding engine needs, for both
PurchaseBill.paid_amount/balance_amount/status (PurchaseService) and
Supplier.outstanding_amount (SupplierService) - TASKS.md Sprint 12 Session 4
explicitly asks for all three pure functions (calculate_purchase_bill_payment,
determine_purchase_bill_status, calculate_supplier_outstanding) to live in
this one module, even though the fields they compute belong to two different
modules. Each owning service (PurchaseService, SupplierService) imports what
it needs from here and applies/persists the result itself - this module never
touches a repository or session.

SupplierPaymentService never calls these functions directly; it only
computes the raw allocation sums (via its own SupplierPaymentRepository) and
passes them to PurchaseService.recalculate_payment_totals, keeping the call
chain SupplierPaymentService -> PurchaseService -> SupplierService
(ARCHITECTURE.md §2).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from app.modules.purchase.constants import PurchaseStatus

_TWO_PLACES: Final = Decimal("0.01")

# Purchase bills outside these three statuses (draft, cancelled) are not part
# of the payment lifecycle - allocations can only ever be created against a
# POSTED/PARTIALLY_PAID purchase bill (see
# SupplierPaymentService._ensure_purchase_bill_allocatable), so a DRAFT/
# CANCELLED bill should never reach this engine at all.
_RECONCILABLE_PURCHASE_BILL_STATUSES: Final = frozenset(
    {PurchaseStatus.POSTED, PurchaseStatus.PARTIALLY_PAID, PurchaseStatus.PAID}
)


class ReconciliationError(ValueError):
    """Base class for domain-level outstanding-engine invariant violations.

    A plain ValueError, not an app.core.errors.AppException subclass - this
    module has no dependency on the outer layers. PurchaseService/
    SupplierService each translate these into their own application-layer
    exception at the boundary (PurchaseBillReconciliationError/
    SupplierOutstandingCalculationError).
    """


class NegativePaidAmountError(ReconciliationError):
    """A recomputed paid_amount came out negative.

    Not reachable in practice - SUM() over allocated_amount columns that are
    themselves constrained > 0 (SupplierPaymentAllocationCreateRequest) can
    never be negative - the same last-line-of-defense posture
    purchase/domain/totals.NegativeTotalError documents.
    """


class PaidAmountExceedsTotalError(ReconciliationError):
    """A recomputed paid_amount exceeds the purchase bill's total_amount.

    Not reachable in practice - SupplierPaymentService's allocation ceilings
    (app.modules.supplier_payments.domain.allocation) already keep every
    allocation within the purchase bill's balance_amount at the moment it is
    created or updated. Defense in depth, exercised directly against this
    module's functions in tests.
    """


class NegativeBalanceAmountError(ReconciliationError):
    """A recomputed balance_amount came out negative. Implied by
    PaidAmountExceedsTotalError's guard passing, but checked independently so
    this module never depends on check ordering to stay correct."""


class PurchaseBillNotReconcilableError(ReconciliationError):
    """The purchase bill's current status (draft or cancelled) is outside the
    payment lifecycle - TASKS.md's "Prevent invalid status transitions". Not
    reachable in practice - only POSTED/PARTIALLY_PAID purchase bills can
    ever receive an allocation in the first place, and PAID is reachable only
    as this engine's own output - but guarded explicitly so a draft or
    cancelled purchase bill can never have its status silently overwritten by
    a stale allocation mutation."""


class NegativeOutstandingError(ReconciliationError):
    """A recomputed Supplier.outstanding_amount came out negative.

    Not reachable in practice - it is a SUM of purchase_bills.balance_amount,
    which PurchaseService's own reconciliation guard never lets go negative -
    but checked here too since SupplierService owns this field and must not
    trust an input it did not itself validate.
    """


@dataclass(frozen=True, slots=True)
class PurchaseBillPaymentTotals:
    """PurchaseBill.paid_amount/balance_amount/status after a recompute."""

    paid_amount: Decimal
    balance_amount: Decimal
    status: PurchaseStatus


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def determine_purchase_bill_status(
    *, total_amount: Decimal, balance_amount: Decimal
) -> PurchaseStatus:
    """TASKS.md Sprint 12 Session 4's status rule:

        balance == total  -> POSTED           (nothing paid yet)
        balance == 0      -> PAID             (fully settled)
        otherwise         -> PARTIALLY_PAID

    Checked in that order: a purchase bill with total_amount == 0 (no items)
    has balance_amount == total_amount == 0 and is reported POSTED, not PAID -
    "nothing owed" takes precedence over "nothing outstanding" when both are
    simultaneously true.
    """
    if balance_amount == total_amount:
        return PurchaseStatus.POSTED
    if balance_amount == 0:
        return PurchaseStatus.PAID
    return PurchaseStatus.PARTIALLY_PAID


def calculate_purchase_bill_payment(
    *, total_amount: Decimal, total_allocated: Decimal, current_status: PurchaseStatus
) -> PurchaseBillPaymentTotals:
    """PurchaseBill.paid_amount/balance_amount/status, recomputed from
    scratch (TASKS.md Sprint 12 Session 4 formulas):

        paid_amount    = SUM(supplier_payment_allocations)
        balance_amount = total_amount - paid_amount
        status         = determine_purchase_bill_status(...)

    `total_allocated` is the sum of every currently-active allocation across
    every supplier payment for this purchase bill (computed by
    SupplierPaymentService via its own SupplierPaymentRepository - this
    function never sums rows itself). `current_status` guards against
    recalculating a purchase bill outside the payment lifecycle (see
    PurchaseBillNotReconcilableError) - checked first, before any arithmetic.
    """
    if current_status not in _RECONCILABLE_PURCHASE_BILL_STATUSES:
        raise PurchaseBillNotReconcilableError(
            f"Purchase bill status {current_status} is not eligible for payment reconciliation"
        )

    paid_amount = _round_money(total_allocated)
    if paid_amount < 0:
        raise NegativePaidAmountError(f"Computed paid amount {paid_amount} is negative")
    if paid_amount > total_amount:
        raise PaidAmountExceedsTotalError(
            f"Computed paid amount {paid_amount} exceeds the purchase bill's total {total_amount}"
        )

    balance_amount = _round_money(total_amount - paid_amount)
    if balance_amount < 0:
        raise NegativeBalanceAmountError(f"Computed balance amount {balance_amount} is negative")

    status = determine_purchase_bill_status(
        total_amount=total_amount, balance_amount=balance_amount
    )
    return PurchaseBillPaymentTotals(
        paid_amount=paid_amount, balance_amount=balance_amount, status=status
    )


def calculate_supplier_outstanding(*, total_open_balance: Decimal) -> Decimal:
    """Supplier.outstanding_amount, recomputed from the sum of balance_amount
    across every open (POSTED or PARTIALLY_PAID) purchase bill for this
    supplier - already aggregated server-side by
    PurchaseRepository.sum_open_balance_by_supplier (a SQL SUM, not fetched
    row-by-row into Python - ARCHITECTURE.md's N+1-avoidance rule applies
    equally to aggregation). Never patched incrementally (TASKS.md: "Never
    increment. Always recompute from source."), unlike
    SupplierService.increase_outstanding's atomic += used by the Sprint 11
    Session 5 posting workflow.
    """
    outstanding_amount = _round_money(total_open_balance)
    if outstanding_amount < 0:
        raise NegativeOutstandingError(
            f"Computed outstanding amount {outstanding_amount} is negative"
        )
    return outstanding_amount
