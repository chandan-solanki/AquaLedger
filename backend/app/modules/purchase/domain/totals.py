"""Sprint 11 Session 4 - server-side financial calculation engine.

Pure domain logic: no SQLAlchemy, no FastAPI, no I/O (ARCHITECTURE.md §1.3's
Domain Layer "knows nothing about FastAPI, SQLAlchemy, or Redis"). Money math
is Decimal-only throughout - never float (ARCHITECTURE.md §5.1's "Always use
Decimal... Never use float for financial calculations") - and every monetary
result is rounded HALF_UP to 2 decimal places, matching every NUMERIC(14,2)
money column on `purchase_bills`/`purchase_bill_items`. Mirrors
app.modules.invoices.domain.totals exactly, on the buy side.

PurchaseService is the only caller. It never trusts a client-supplied
financial field (see PurchaseBillItemCreateRequest/PurchaseBillItemUpdateRequest's
docstrings) - this module is where those totals actually get computed, and
PurchaseService._recalculate_purchase_bill is what wires it into the database.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

_TWO_PLACES: Final = Decimal("0.01")
_HUNDRED: Final = Decimal("100")

# NUMERIC(14,2): 14 total digits, 2 after the decimal point, so the integer
# part can be at most 12 digits long. Applies equally to purchase_bill_items'
# discount_amount/taxable_amount/tax_amount/line_total and to purchase_bills'
# subtotal/discount_amount/taxable_amount/tax_amount/total_amount/
# balance_amount - every column this module computes shares the same shape.
MAX_MONEY: Final = Decimal("999999999999.99")


class FinancialCalculationError(ValueError):
    """Base class for domain-level financial invariant violations.

    A plain ValueError, not an app.core.errors.AppException subclass - this
    module has no dependency on the outer layers. PurchaseService translates
    this into PURCHASE_CALCULATION_ERROR at the application-layer boundary
    (app.modules.purchase.exceptions.PurchaseCalculationError).
    """


class NegativeTotalError(FinancialCalculationError):
    """A computed total came out negative.

    Not reachable through the API as it stands - quantity>0, rate>=0, and
    0<=discount_percent/tax_rate<=100 are already enforced by
    PurchaseBillItemCreateRequest/PurchaseBillItemUpdateRequest (Session 3),
    and transport_charge/other_charge/round_off stay at their server-owned
    default of 0 (no request field sets them yet) - which together guarantee
    every formula below stays non-negative. This is the last line of defense
    the task's "reject negative totals" rule asks for, and is exercised
    directly against this module's functions in tests.
    """


class TotalOverflowError(FinancialCalculationError):
    """A computed total exceeds MAX_MONEY - what a NUMERIC(14,2) column can
    store. Reachable in practice: quantity (up to 12,3) and rate (up to
    12,4) are independently bounded but their product is not, so a
    sufficiently large quantity x rate overflows before it ever reaches
    Postgres."""


@dataclass(frozen=True, slots=True)
class LineTotals:
    """The four server-calculated fields of one purchase_bill_items row."""

    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    line_total: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseBillTotals:
    """The full set of a purchase bill's financial columns after
    recalculation.

    transport_charge/other_charge/round_off are echoed straight back from
    the caller's inputs (they are not computed here - see
    calculate_purchase_bill_totals's docstring) purely so PurchaseService can
    assign every financial column on the PurchaseBill row from one result
    object. paid_amount/balance_amount are always 0/total_amount - the
    supplier-payment workflow that would make paid_amount nonzero is Session
    5's job (TASKS.md Session 4: "paid_amount = 0").
    """

    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    transport_charge: Decimal
    other_charge: Decimal
    round_off: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal


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
    """One purchase_bill_items row's discount_amount/taxable_amount/
    tax_amount/line_total (TASKS.md Sprint 11 Session 4 line formulas):

        gross_amount    = qty * rate
        discount_amount = gross_amount * discount% / 100
        taxable_amount  = gross_amount - discount_amount
        tax_amount      = taxable_amount * tax% / 100
        line_total      = taxable_amount + tax_amount

    Every intermediate is Decimal (never float). Each monetary result is
    rounded HALF_UP to 2 decimal places - the precision purchase_bill_items'
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


def calculate_purchase_bill_totals(
    line_totals: list[LineTotals],
    *,
    transport_charge: Decimal,
    other_charge: Decimal,
    round_off: Decimal,
) -> PurchaseBillTotals:
    """A purchase bill's aggregate financial columns (TASKS.md Sprint 11
    Session 4 purchase bill formulas):

        subtotal        = sum(line_total)          -- tax-inclusive, per line
        discount_amount  = sum(line discount_amount)
        taxable_amount   = sum(line taxable_amount)
        tax_amount       = sum(line tax_amount)
        total_amount     = subtotal + transport_charge + other_charge + round_off
        paid_amount      = 0
        balance_amount   = total_amount

    `subtotal` sums each line's tax-inclusive `line_total` (not the pre-tax
    taxable amount - that aggregate is `taxable_amount`), so `total_amount`
    adds transport/other/round-off on top of it directly without also
    adding `tax_amount` again; `tax_amount` on the bill is a breakdown
    figure for display, not a second addend.

    `transport_charge`/`other_charge`/`round_off` are inputs, not outputs:
    they are read straight off the PurchaseBill row (none is client-settable
    yet - PurchaseBillCreateRequest/PurchaseBillUpdateRequest don't accept
    them, TASKS.md Sprint 11 Session 2's "Server owns" list), so they are
    always 0 in practice this session. They are echoed back on
    PurchaseBillTotals purely so the caller can assign every bill financial
    column from a single result object. `paid_amount` is always 0 and
    `balance_amount` always equals `total_amount` - the supplier-payment
    integration that would make either otherwise is Session 5's job
    (TASKS.md Session 4 explicit: "do not implement supplier payments").
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
    paid_amount = Decimal("0")
    balance_amount = total_amount
    return PurchaseBillTotals(
        subtotal=subtotal,
        discount_amount=discount_amount,
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        transport_charge=transport_charge,
        other_charge=other_charge,
        round_off=round_off,
        total_amount=total_amount,
        paid_amount=paid_amount,
        balance_amount=balance_amount,
    )
