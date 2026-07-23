"""Sprint 10 Session 4 - the outstanding/reconciliation engine
(ARCHITECTURE.md §5.3's "never present a stored aggregate you cannot
re-derive on demand").

Pure domain logic: no SQLAlchemy, no FastAPI, no I/O (ARCHITECTURE.md §1.3's
Domain Layer). Money math is Decimal-only throughout, ROUND_HALF_UP to 2
decimal places - the same discipline invoices/domain/totals.py and
payments/domain/allocation.py apply to their own calculations.

Holds every financial calculation the outstanding engine needs, for both
Invoice.paid_amount/balance_amount/status (InvoiceService) and
Company.outstanding_amount (CompanyService) - TASKS.md Sprint 10 Session 4
explicitly asks for all three pure functions (calculate_invoice_payment,
determine_invoice_status, calculate_company_outstanding) to live in this one
module, even though the fields they compute belong to two different modules.
Each owning service (InvoiceService, CompanyService) imports what it needs
from here and applies/persists the result itself - this module never touches
a repository or session.

PaymentService never calls these functions directly; it only computes the
raw allocation sums (via its own PaymentRepository) and passes them to
InvoiceService.recalculate_payment_totals, keeping the call chain
PaymentService -> InvoiceService -> CompanyService (ARCHITECTURE.md §2).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from app.modules.invoices.constants import InvoiceStatus

_TWO_PLACES: Final = Decimal("0.01")

# Invoices outside these three statuses (draft, cancelled) are not part of
# the payment lifecycle - allocations can only ever be created against an
# ISSUED/PARTIALLY_PAID invoice (see payments/service.py's
# _ALLOCATABLE_INVOICE_STATUSES), so a DRAFT/CANCELLED invoice should never
# reach this engine at all.
_RECONCILABLE_INVOICE_STATUSES: Final = frozenset(
    {InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.PAID}
)


class ReconciliationError(ValueError):
    """Base class for domain-level outstanding-engine invariant violations.

    A plain ValueError, not an app.core.errors.AppException subclass - this
    module has no dependency on the outer layers. InvoiceService/
    CompanyService each translate these into their own application-layer
    exception at the boundary (InvoiceReconciliationError/
    CompanyOutstandingCalculationError).
    """


class NegativePaidAmountError(ReconciliationError):
    """A recomputed paid_amount came out negative.

    Not reachable in practice - SUM() over allocated_amount columns that are
    themselves constrained > 0 (PaymentAllocationCreateRequest) can never be
    negative - the same last-line-of-defense posture
    invoices/domain/totals.NegativeTotalError documents.
    """


class PaidAmountExceedsTotalError(ReconciliationError):
    """A recomputed paid_amount exceeds the invoice's total_amount.

    Not reachable in practice - PaymentService's allocation ceilings
    (app.modules.payments.domain.allocation) already keep every allocation
    within the invoice's balance_amount at the moment it is created or
    updated. Defense in depth, exercised directly against this module's
    functions in tests.
    """


class NegativeBalanceAmountError(ReconciliationError):
    """A recomputed balance_amount came out negative. Implied by
    PaidAmountExceedsTotalError's guard passing, but checked independently
    so this module never depends on check ordering to stay correct."""


class InvoiceNotReconcilableError(ReconciliationError):
    """The invoice's current status (draft or cancelled) is outside the
    payment lifecycle - TASKS.md's "Prevent invalid invoice status
    transitions". Not reachable in practice - only ISSUED/PARTIALLY_PAID
    invoices can ever receive an allocation in the first place, and PAID is
    reachable only as this engine's own output - but guarded explicitly so a
    draft or cancelled invoice can never have its status silently
    overwritten by a stale allocation mutation."""


class NegativeOutstandingError(ReconciliationError):
    """A recomputed Company.outstanding_amount came out negative.

    Not reachable in practice - it is a SUM of invoices.balance_amount,
    which InvoiceService's own reconciliation guard never lets go negative -
    but checked here too since CompanyService owns this field and must not
    trust an input it did not itself validate.
    """


@dataclass(frozen=True, slots=True)
class InvoicePaymentTotals:
    """Invoice.paid_amount/balance_amount/status after a recompute."""

    paid_amount: Decimal
    balance_amount: Decimal
    status: InvoiceStatus


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def determine_invoice_status(*, total_amount: Decimal, balance_amount: Decimal) -> InvoiceStatus:
    """TASKS.md Sprint 10 Session 4's status rule:

        balance == total  -> ISSUED           (nothing paid yet)
        balance == 0      -> PAID             (fully settled)
        otherwise         -> PARTIALLY_PAID

    Checked in that order: an invoice with total_amount == 0 (no items) has
    balance_amount == total_amount == 0 and is reported ISSUED, not PAID -
    "nothing owed" takes precedence over "nothing outstanding" when both are
    simultaneously true.
    """
    if balance_amount == total_amount:
        return InvoiceStatus.ISSUED
    if balance_amount == 0:
        return InvoiceStatus.PAID
    return InvoiceStatus.PARTIALLY_PAID


def calculate_invoice_payment(
    *, total_amount: Decimal, total_allocated: Decimal, current_status: InvoiceStatus
) -> InvoicePaymentTotals:
    """Invoice.paid_amount/balance_amount/status, recomputed from scratch
    (TASKS.md Sprint 10 Session 4 formulas):

        paid_amount    = SUM(payment_allocations)
        balance_amount = total_amount - paid_amount
        status         = determine_invoice_status(...)

    `total_allocated` is the sum of every currently-active allocation across
    every payment for this invoice (computed by PaymentService via its own
    PaymentRepository - this function never sums rows itself). `current_status`
    guards against recalculating an invoice outside the payment lifecycle
    (see InvoiceNotReconcilableError) - checked first, before any arithmetic.
    """
    if current_status not in _RECONCILABLE_INVOICE_STATUSES:
        raise InvoiceNotReconcilableError(
            f"Invoice status {current_status} is not eligible for payment reconciliation"
        )

    paid_amount = _round_money(total_allocated)
    if paid_amount < 0:
        raise NegativePaidAmountError(f"Computed paid amount {paid_amount} is negative")
    if paid_amount > total_amount:
        raise PaidAmountExceedsTotalError(
            f"Computed paid amount {paid_amount} exceeds the invoice's total {total_amount}"
        )

    balance_amount = _round_money(total_amount - paid_amount)
    if balance_amount < 0:
        raise NegativeBalanceAmountError(f"Computed balance amount {balance_amount} is negative")

    status = determine_invoice_status(total_amount=total_amount, balance_amount=balance_amount)
    return InvoicePaymentTotals(
        paid_amount=paid_amount, balance_amount=balance_amount, status=status
    )


def calculate_company_outstanding(*, total_open_balance: Decimal) -> Decimal:
    """Company.outstanding_amount, recomputed from the sum of balance_amount
    across every open (ISSUED or PARTIALLY_PAID) invoice for this company -
    already aggregated server-side by InvoiceRepository.sum_open_balance_by_company
    (a SQL SUM, not fetched row-by-row into Python - ARCHITECTURE.md's
    N+1-avoidance rule applies equally to aggregation). Never patched
    incrementally (TASKS.md: "Do NOT increment/decrement. Recompute."),
    unlike CompanyService.increase_outstanding's atomic += used by the
    Sprint 9 issue workflow.
    """
    outstanding_amount = _round_money(total_open_balance)
    if outstanding_amount < 0:
        raise NegativeOutstandingError(
            f"Computed outstanding amount {outstanding_amount} is negative"
        )
    return outstanding_amount
