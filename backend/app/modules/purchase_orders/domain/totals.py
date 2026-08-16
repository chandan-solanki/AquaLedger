"""Server-side financial calculation engine for purchase orders, mirroring
app.modules.purchase.domain.totals exactly.

Pure domain logic: no SQLAlchemy, no FastAPI, no I/O (ARCHITECTURE.md §1.3's
Domain Layer "knows nothing about FastAPI, SQLAlchemy, or Redis"). Money math
is Decimal-only throughout - never float (ARCHITECTURE.md §5.1) - and every
monetary result is rounded HALF_UP to 2 decimal places, matching every
NUMERIC(14,2) money column on `purchase_orders`/`purchase_order_items`.

PurchaseOrderService is the only caller. It never trusts a client-supplied
financial field - this module is where those totals actually get computed.

Unlike app.modules.purchase.domain.totals, there is no paid_amount/
balance_amount here: a purchase order is never paid (ARCHITECTURE.md's
Business Model - a PO is a commitment, not a bill), so PurchaseOrderTotals
carries only the document's own financial columns.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

_TWO_PLACES: Final = Decimal("0.01")
_HUNDRED: Final = Decimal("100")

# NUMERIC(14,2): 14 total digits, 2 after the decimal point, so the integer
# part can be at most 12 digits long. Applies equally to purchase_order_items'
# discount_amount/taxable_amount/tax_amount/line_total and to purchase_orders'
# subtotal/discount_amount/taxable_amount/tax_amount/total_amount.
MAX_MONEY: Final = Decimal("999999999999.99")


class FinancialCalculationError(ValueError):
    """Base class for domain-level financial invariant violations.

    A plain ValueError, not an app.core.errors.AppException subclass - this
    module has no dependency on the outer layers. PurchaseOrderService
    translates this into PURCHASE_ORDER_CALCULATION_ERROR at the
    application-layer boundary.
    """


class NegativeTotalError(FinancialCalculationError):
    """A computed total came out negative.

    Not reachable through the API as it stands - quantity>0, rate>=0, and
    0<=discount_percent/tax_rate<=100 are already enforced by
    PurchaseOrderItemCreateRequest/PurchaseOrderItemUpdateRequest, and
    transport_charge/other_charge/round_off stay at their server-owned
    default of 0 - which together guarantee every formula below stays
    non-negative. This is the last line of defense the task's "reject
    negative totals" rule asks for, and is exercised directly against this
    module's functions in tests.
    """


class TotalOverflowError(FinancialCalculationError):
    """A computed total exceeds MAX_MONEY - what a NUMERIC(14,2) column can
    store. Reachable in practice: quantity (up to 12,3) and rate (up to
    12,4) are independently bounded but their product is not, so a
    sufficiently large quantity x rate overflows before it ever reaches
    Postgres."""


@dataclass(frozen=True, slots=True)
class LineTotals:
    """The four server-calculated fields of one purchase_order_items row."""

    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    line_total: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseOrderTotals:
    """The full set of a purchase order's financial columns after
    recalculation.

    transport_charge/other_charge/round_off are echoed straight back from
    the caller's inputs (they are not computed here) purely so
    PurchaseOrderService can assign every financial column on the
    PurchaseOrder row from one result object.
    """

    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    transport_charge: Decimal
    other_charge: Decimal
    round_off: Decimal
    total_amount: Decimal


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _validated(value: Decimal) -> Decimal:
    if value < 0:
        raise NegativeTotalError(f"Computed total {value} is negative")
    if value > MAX_MONEY:
        raise TotalOverflowError(f"Computed total {value} exceeds {MAX_MONEY}")
    return value


def calculate_line_totals(
    *, quantity: Decimal, rate: Decimal, discount_percent: Decimal, tax_rate: Decimal
) -> LineTotals:
    """One purchase_order_items row's discount_amount/taxable_amount/
    tax_amount/line_total:

        gross_amount    = qty * rate
        discount_amount = gross_amount * discount% / 100
        taxable_amount  = gross_amount - discount_amount
        tax_amount      = taxable_amount * tax% / 100
        line_total      = taxable_amount + tax_amount

    Every intermediate is Decimal (never float). Each monetary result is
    rounded HALF_UP to 2 decimal places - the precision purchase_order_items'
    columns actually store - before being used in the next step, so what's
    returned here is exactly what gets persisted; there is no further
    rounding downstream.
    """
    gross_amount = quantity * rate
    discount_amount = _validated(_round_money(gross_amount * discount_percent / _HUNDRED))
    taxable_amount = _validated(_round_money(gross_amount - discount_amount))
    tax_amount = _validated(_round_money(taxable_amount * tax_rate / _HUNDRED))
    line_total = _validated(_round_money(taxable_amount + tax_amount))
    return LineTotals(
        discount_amount=discount_amount,
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        line_total=line_total,
    )


def calculate_purchase_order_totals(
    line_totals: list[LineTotals],
    *,
    transport_charge: Decimal,
    other_charge: Decimal,
    round_off: Decimal,
) -> PurchaseOrderTotals:
    """A purchase order's aggregate financial columns:

        subtotal        = sum(line_total)          -- tax-inclusive, per line
        discount_amount  = sum(line discount_amount)
        taxable_amount   = sum(line taxable_amount)
        tax_amount       = sum(line tax_amount)
        total_amount     = subtotal + transport_charge + other_charge + round_off

    `subtotal` sums each line's tax-inclusive `line_total` (not the pre-tax
    taxable amount - that aggregate is `taxable_amount`), so `total_amount`
    adds transport/other/round-off on top of it directly without also
    adding `tax_amount` again; `tax_amount` on the order is a breakdown
    figure for display, not a second addend.

    `transport_charge`/`other_charge`/`round_off` are inputs, not outputs:
    they are read straight off the PurchaseOrder row (none is client-settable
    yet), so they are always 0 in practice this session. They are echoed
    back on PurchaseOrderTotals purely so the caller can assign every order
    financial column from a single result object.
    """
    subtotal = _validated(_round_money(sum((lt.line_total for lt in line_totals), Decimal("0"))))
    discount_amount = _validated(
        _round_money(sum((lt.discount_amount for lt in line_totals), Decimal("0")))
    )
    taxable_amount = _validated(
        _round_money(sum((lt.taxable_amount for lt in line_totals), Decimal("0")))
    )
    tax_amount = _validated(_round_money(sum((lt.tax_amount for lt in line_totals), Decimal("0"))))
    total_amount = _validated(_round_money(subtotal + transport_charge + other_charge + round_off))
    return PurchaseOrderTotals(
        subtotal=subtotal,
        discount_amount=discount_amount,
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        transport_charge=transport_charge,
        other_charge=other_charge,
        round_off=round_off,
        total_amount=total_amount,
    )
