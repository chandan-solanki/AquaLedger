"""Sprint 12 Session 3 - the supplier payment allocation engine
(ARCHITECTURE.md §14.2, applied to the buy side).

Pure domain logic: no SQLAlchemy, no FastAPI, no I/O (ARCHITECTURE.md §1.3's
Domain Layer "knows nothing about FastAPI, SQLAlchemy, or Redis"). Money math
is Decimal-only throughout - never float (ARCHITECTURE.md §5.1) - mirroring
the discipline app.modules.payments.domain.allocation applies on the sell
side.

SupplierPaymentService is the only caller. It never trusts a client-supplied
allocated_amount total - this module is where the two allocation ceilings
(TASKS.md Sprint 12 Session 3) are actually checked, and where
SupplierPayment.allocated_amount/unallocated_amount are recomputed from the
sum of that payment's currently-active allocations - the same
recompute-from-source discipline PaymentService._recalculate_payment_allocation_totals
applies, rather than incrementally patching values that can drift.

Deliberately out of scope here (TASKS.md: "Do not update Purchase Bill
financials yet"): PurchaseBill.paid_amount/balance_amount/status and
Supplier.outstanding_amount are untouched by this module -
PurchaseBill.balance_amount is only ever *read*, never written, until the
Session 4 outstanding-reconciliation engine exists.
"""

from dataclasses import dataclass
from decimal import Decimal


class AllocationValidationError(ValueError):
    """Base class for domain-level allocation invariant violations.

    A plain ValueError, not an app.core.errors.AppException subclass - this
    module has no dependency on the outer layers. SupplierPaymentService
    translates each of these into the matching
    app.modules.supplier_payments.exceptions class at the application-layer
    boundary.
    """


class AllocationExceedsPurchaseBillBalanceError(AllocationValidationError):
    """allocated_amount > the purchase bill's current balance_amount."""


class AllocationExceedsUnallocatedError(AllocationValidationError):
    """allocated_amount > the supplier payment's current unallocated_amount."""


@dataclass(frozen=True, slots=True)
class SupplierPaymentAllocationTotals:
    """SupplierPayment.allocated_amount/unallocated_amount after a recompute."""

    allocated_amount: Decimal
    unallocated_amount: Decimal


def validate_allocation_amount(
    *,
    allocated_amount: Decimal,
    purchase_bill_balance: Decimal,
    payment_unallocated: Decimal,
) -> None:
    """TASKS.md Sprint 12 Session 3's two allocation ceilings:

        allocated_amount <= purchase_bill.balance_amount
        allocated_amount <= supplier_payment.unallocated_amount

    Checked independently, both against the state *before* this allocation
    is applied, so each violation reports its own specific error. For an
    update, the caller passes `payment_unallocated` as the payment's current
    unallocated_amount *plus* the allocation's own prior amount (that amount
    is already "spent" against it and must be added back before comparing
    against the new amount) - and, when the allocation's target bill is
    unchanged, `purchase_bill_balance` gets the same add-back treatment (see
    SupplierPaymentService.update_allocation's docstring).
    """
    if allocated_amount > purchase_bill_balance:
        raise AllocationExceedsPurchaseBillBalanceError(
            f"Allocated amount {allocated_amount} exceeds the purchase bill's balance "
            f"{purchase_bill_balance}"
        )
    if allocated_amount > payment_unallocated:
        raise AllocationExceedsUnallocatedError(
            f"Allocated amount {allocated_amount} exceeds the payment's unallocated amount "
            f"{payment_unallocated}"
        )


def calculate_supplier_payment_allocation_totals(
    *, payment_amount: Decimal, total_allocated: Decimal
) -> SupplierPaymentAllocationTotals:
    """SupplierPayment.allocated_amount/unallocated_amount from scratch,
    given the sum of that payment's currently-active allocations.
    `total_allocated` is always <= `payment_amount` in practice - every
    allocation that contributed to it was already validated against the
    payment's unallocated_amount at the time it was created or updated -
    but this performs no additional clamping itself; it is a pure
    recomputation, not a second validation pass.
    """
    return SupplierPaymentAllocationTotals(
        allocated_amount=total_allocated,
        unallocated_amount=payment_amount - total_allocated,
    )
