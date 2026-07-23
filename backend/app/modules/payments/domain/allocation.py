"""Sprint 10 Session 3 - the payment allocation engine (ARCHITECTURE.md §14.2).

Pure domain logic: no SQLAlchemy, no FastAPI, no I/O (ARCHITECTURE.md §1.3's
Domain Layer "knows nothing about FastAPI, SQLAlchemy, or Redis"). Money math
is Decimal-only throughout - never float (ARCHITECTURE.md §5.1) - mirroring
the discipline invoices/domain/totals.py applies to invoice financials.

PaymentService is the only caller. It never trusts a client-supplied
allocated_amount total - this module is where the two allocation ceilings
(TASKS.md Sprint 10 Session 3) are actually checked, and where
Payment.allocated_amount/unallocated_amount are recomputed from the sum of
that payment's currently-active allocations - the same recompute-from-source
discipline InvoiceService._recalculate_invoice applies to invoice totals,
rather than incrementally patching values that can drift.

Deliberately out of scope here (TASKS.md: "Do NOT update invoice
financials"): Invoice.paid_amount/balance_amount/status are untouched by
this module - Invoice.balance_amount is only ever *read*, never written,
until the Session 4 outstanding engine exists.
"""

from dataclasses import dataclass
from decimal import Decimal


class AllocationValidationError(ValueError):
    """Base class for domain-level allocation invariant violations.

    A plain ValueError, not an app.core.errors.AppException subclass - this
    module has no dependency on the outer layers. PaymentService translates
    each of these into the matching app.modules.payments.exceptions class at
    the application-layer boundary.
    """


class AllocationExceedsInvoiceBalanceError(AllocationValidationError):
    """allocated_amount > the invoice's current balance_amount."""


class AllocationExceedsUnallocatedError(AllocationValidationError):
    """allocated_amount > the payment's current unallocated_amount."""


@dataclass(frozen=True, slots=True)
class PaymentAllocationTotals:
    """Payment.allocated_amount/unallocated_amount after a recompute."""

    allocated_amount: Decimal
    unallocated_amount: Decimal


def validate_allocation_amount(
    *,
    allocated_amount: Decimal,
    invoice_balance: Decimal,
    payment_unallocated: Decimal,
) -> None:
    """TASKS.md Sprint 10 Session 3's two allocation ceilings:

        allocated_amount <= invoice.balance_amount
        allocated_amount <= payment.unallocated_amount

    Checked independently, both against the state *before* this allocation
    is applied, so each violation reports its own specific error. For an
    update, the caller passes `payment_unallocated` as the payment's current
    unallocated_amount *plus* the allocation's own prior amount (that amount
    is already "spent" against it and must be added back before comparing
    against the new amount) - `invoice_balance` needs no equivalent
    adjustment, since this module never writes to it (see module docstring).
    """
    if allocated_amount > invoice_balance:
        raise AllocationExceedsInvoiceBalanceError(
            f"Allocated amount {allocated_amount} exceeds the invoice's balance {invoice_balance}"
        )
    if allocated_amount > payment_unallocated:
        raise AllocationExceedsUnallocatedError(
            f"Allocated amount {allocated_amount} exceeds the payment's unallocated amount "
            f"{payment_unallocated}"
        )


def calculate_payment_allocation_totals(
    *, payment_amount: Decimal, total_allocated: Decimal
) -> PaymentAllocationTotals:
    """Payment.allocated_amount/unallocated_amount from scratch, given the
    sum of that payment's currently-active allocations. `total_allocated` is
    always <= `payment_amount` in practice - every allocation that
    contributed to it was already validated against the payment's
    unallocated_amount at the time it was created or updated - but this
    performs no additional clamping itself; it is a pure recomputation, not
    a second validation pass.
    """
    return PaymentAllocationTotals(
        allocated_amount=total_allocated,
        unallocated_amount=payment_amount - total_allocated,
    )
