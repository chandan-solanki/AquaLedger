import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.reports.constants import (
    EntityType,
    PaidStatus,
    ProfitabilityFilter,
    RiskLevel,
    SupplierTransactionType,
    TransactionType,
)
from app.modules.reports.schemas import (
    AgingReportParams,
    BoatProfitabilityParams,
    CustomerLedgerParams,
    FishSalesHistoryParams,
    FishSalesParams,
    OutstandingReportParams,
    PurchaseReportParams,
    SalesReportParams,
    SupplierLedgerParams,
    TripProfitabilityParams,
)

_MINIMAL: dict[str, object] = {"customer_id": uuid.uuid4()}
_SUPPLIER_MINIMAL: dict[str, object] = {"supplier_id": uuid.uuid4()}


class TestCustomerLedgerParams:
    def test_minimal_payload_gets_sane_defaults(self) -> None:
        params = CustomerLedgerParams(**_MINIMAL)
        assert params.from_date is None
        assert params.to_date is None
        assert params.transaction_type is None
        assert params.page == 1
        assert params.page_size == 20

    def test_rejects_missing_customer_id(self) -> None:
        with pytest.raises(ValidationError):
            CustomerLedgerParams()

    def test_rejects_invalid_customer_id(self) -> None:
        with pytest.raises(ValidationError):
            CustomerLedgerParams(customer_id="not-a-uuid")

    def test_accepts_equal_from_and_to_date(self) -> None:
        params = CustomerLedgerParams(
            **_MINIMAL, from_date=date(2026, 7, 1), to_date=date(2026, 7, 1)
        )
        assert params.from_date == params.to_date

    def test_accepts_from_date_before_to_date(self) -> None:
        params = CustomerLedgerParams(
            **_MINIMAL, from_date=date(2026, 7, 1), to_date=date(2026, 7, 31)
        )
        assert params.from_date is not None
        assert params.to_date is not None

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            CustomerLedgerParams(**_MINIMAL, from_date=date(2026, 7, 31), to_date=date(2026, 7, 1))

    def test_accepts_only_from_date(self) -> None:
        params = CustomerLedgerParams(**_MINIMAL, from_date=date(2026, 7, 1))
        assert params.to_date is None

    def test_accepts_only_to_date(self) -> None:
        params = CustomerLedgerParams(**_MINIMAL, to_date=date(2026, 7, 31))
        assert params.from_date is None

    def test_accepts_transaction_type_values(self) -> None:
        invoice_params = CustomerLedgerParams(**_MINIMAL, transaction_type="invoice")
        payment_params = CustomerLedgerParams(**_MINIMAL, transaction_type="payment")
        assert invoice_params.transaction_type == TransactionType.INVOICE
        assert payment_params.transaction_type == TransactionType.PAYMENT

    def test_rejects_invalid_transaction_type(self) -> None:
        with pytest.raises(ValidationError):
            CustomerLedgerParams(**_MINIMAL, transaction_type="refund")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            CustomerLedgerParams(**_MINIMAL, page=0)

    def test_rejects_page_size_below_one(self) -> None:
        with pytest.raises(ValidationError):
            CustomerLedgerParams(**_MINIMAL, page_size=0)

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            CustomerLedgerParams(**_MINIMAL, page_size=101)

    def test_accepts_page_size_at_upper_bound(self) -> None:
        params = CustomerLedgerParams(**_MINIMAL, page_size=100)
        assert params.page_size == 100


class TestSupplierLedgerParams:
    """Mirrors TestCustomerLedgerParams exactly, on the buy side."""

    def test_minimal_payload_gets_sane_defaults(self) -> None:
        params = SupplierLedgerParams(**_SUPPLIER_MINIMAL)
        assert params.from_date is None
        assert params.to_date is None
        assert params.transaction_type is None
        assert params.page == 1
        assert params.page_size == 20

    def test_rejects_missing_supplier_id(self) -> None:
        with pytest.raises(ValidationError):
            SupplierLedgerParams()

    def test_rejects_invalid_supplier_id(self) -> None:
        with pytest.raises(ValidationError):
            SupplierLedgerParams(supplier_id="not-a-uuid")

    def test_accepts_equal_from_and_to_date(self) -> None:
        params = SupplierLedgerParams(
            **_SUPPLIER_MINIMAL, from_date=date(2026, 7, 1), to_date=date(2026, 7, 1)
        )
        assert params.from_date == params.to_date

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            SupplierLedgerParams(
                **_SUPPLIER_MINIMAL, from_date=date(2026, 7, 31), to_date=date(2026, 7, 1)
            )

    def test_accepts_transaction_type_values(self) -> None:
        bill_params = SupplierLedgerParams(**_SUPPLIER_MINIMAL, transaction_type="purchase_bill")
        payment_params = SupplierLedgerParams(
            **_SUPPLIER_MINIMAL, transaction_type="supplier_payment"
        )
        assert bill_params.transaction_type == SupplierTransactionType.PURCHASE_BILL
        assert payment_params.transaction_type == SupplierTransactionType.SUPPLIER_PAYMENT

    def test_rejects_invalid_transaction_type(self) -> None:
        with pytest.raises(ValidationError):
            SupplierLedgerParams(**_SUPPLIER_MINIMAL, transaction_type="refund")

    def test_rejects_customer_ledger_transaction_type_values(self) -> None:
        """ "invoice"/"payment" are the Customer Ledger's own vocabulary -
        the Supplier Ledger's filter must not accept them."""
        with pytest.raises(ValidationError):
            SupplierLedgerParams(**_SUPPLIER_MINIMAL, transaction_type="invoice")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            SupplierLedgerParams(**_SUPPLIER_MINIMAL, page=0)

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            SupplierLedgerParams(**_SUPPLIER_MINIMAL, page_size=101)


class TestSalesReportParams:
    """TASKS.md Sprint 11 Session 3. Unlike the Ledger params, every field
    is optional - `customer_id` is a filter here, not a required resource
    key, and there is deliberately no `sort` field (the report's order is
    fixed, not user-selectable)."""

    def test_all_fields_are_optional(self) -> None:
        params = SalesReportParams()
        assert params.customer_id is None
        assert params.status is None
        assert params.paid_status is None
        assert params.q is None
        assert params.page == 1
        assert params.page_size == 20

    def test_accepts_equal_from_and_to_date(self) -> None:
        params = SalesReportParams(from_date=date(2026, 7, 1), to_date=date(2026, 7, 1))
        assert params.from_date == params.to_date

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            SalesReportParams(from_date=date(2026, 7, 31), to_date=date(2026, 7, 1))

    def test_accepts_invoice_status_values(self) -> None:
        params = SalesReportParams(status="partially_paid")
        assert params.status is not None

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            SalesReportParams(status="not-a-status")

    def test_accepts_paid_status_values(self) -> None:
        unpaid = SalesReportParams(paid_status="unpaid")
        partial = SalesReportParams(paid_status="partially_paid")
        paid = SalesReportParams(paid_status="paid")
        assert unpaid.paid_status == PaidStatus.UNPAID
        assert partial.paid_status == PaidStatus.PARTIALLY_PAID
        assert paid.paid_status == PaidStatus.PAID

    def test_rejects_invalid_paid_status(self) -> None:
        with pytest.raises(ValidationError):
            SalesReportParams(paid_status="overdue")

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            SalesReportParams(page=0)

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            SalesReportParams(page_size=101)

    def test_has_no_sort_field(self) -> None:
        assert "sort" not in SalesReportParams.model_fields


class TestPurchaseReportParams:
    """Mirrors TestSalesReportParams exactly, on the buy side."""

    def test_all_fields_are_optional(self) -> None:
        params = PurchaseReportParams()
        assert params.supplier_id is None
        assert params.status is None
        assert params.paid_status is None
        assert params.q is None
        assert params.page == 1
        assert params.page_size == 20

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseReportParams(from_date=date(2026, 7, 31), to_date=date(2026, 7, 1))

    def test_accepts_purchase_status_values(self) -> None:
        params = PurchaseReportParams(status="posted")
        assert params.status is not None

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseReportParams(status="not-a-status")

    def test_accepts_paid_status_values(self) -> None:
        params = PurchaseReportParams(paid_status="partially_paid")
        assert params.paid_status == PaidStatus.PARTIALLY_PAID

    def test_rejects_invalid_paid_status(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseReportParams(paid_status="overdue")

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseReportParams(page_size=101)

    def test_has_no_sort_field(self) -> None:
        assert "sort" not in PurchaseReportParams.model_fields


class TestOutstandingReportParams:
    def test_defaults(self) -> None:
        params = OutstandingReportParams()
        assert params.entity_type == EntityType.CUSTOMER
        assert params.outstanding_only is False
        assert params.overdue_only is False
        assert params.risk_level is None
        assert params.from_date is None
        assert params.to_date is None
        assert params.q is None
        assert params.page == 1
        assert params.page_size == 20

    def test_accepts_supplier_entity_type(self) -> None:
        params = OutstandingReportParams(entity_type="supplier")
        assert params.entity_type == EntityType.SUPPLIER

    def test_rejects_invalid_entity_type(self) -> None:
        with pytest.raises(ValidationError):
            OutstandingReportParams(entity_type="vendor")

    def test_accepts_risk_level_values(self) -> None:
        assert OutstandingReportParams(risk_level="low").risk_level == RiskLevel.LOW
        assert OutstandingReportParams(risk_level="medium").risk_level == RiskLevel.MEDIUM
        assert OutstandingReportParams(risk_level="high").risk_level == RiskLevel.HIGH

    def test_rejects_invalid_risk_level(self) -> None:
        with pytest.raises(ValidationError):
            OutstandingReportParams(risk_level="critical")

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            OutstandingReportParams(from_date=date(2026, 7, 31), to_date=date(2026, 7, 1))

    def test_accepts_equal_from_and_to_date(self) -> None:
        params = OutstandingReportParams(from_date=date(2026, 7, 1), to_date=date(2026, 7, 1))
        assert params.from_date == params.to_date

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            OutstandingReportParams(page=0)

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            OutstandingReportParams(page_size=101)

    def test_has_no_sort_field(self) -> None:
        assert "sort" not in OutstandingReportParams.model_fields


class TestAgingReportParams:
    """Mirrors TestOutstandingReportParams, but with a smaller filter set -
    no `overdue_only`, no `from_date`/`to_date`."""

    def test_defaults(self) -> None:
        params = AgingReportParams()
        assert params.entity_type == EntityType.CUSTOMER
        assert params.outstanding_only is False
        assert params.risk_level is None
        assert params.q is None
        assert params.page == 1
        assert params.page_size == 20

    def test_accepts_supplier_entity_type(self) -> None:
        params = AgingReportParams(entity_type="supplier")
        assert params.entity_type == EntityType.SUPPLIER

    def test_rejects_invalid_entity_type(self) -> None:
        with pytest.raises(ValidationError):
            AgingReportParams(entity_type="vendor")

    def test_accepts_risk_level_values(self) -> None:
        assert AgingReportParams(risk_level="high").risk_level == RiskLevel.HIGH

    def test_rejects_invalid_risk_level(self) -> None:
        with pytest.raises(ValidationError):
            AgingReportParams(risk_level="critical")

    def test_has_no_date_range_fields(self) -> None:
        assert "from_date" not in AgingReportParams.model_fields
        assert "to_date" not in AgingReportParams.model_fields

    def test_has_no_overdue_only_field(self) -> None:
        assert "overdue_only" not in AgingReportParams.model_fields

    def test_has_no_sort_field(self) -> None:
        assert "sort" not in AgingReportParams.model_fields

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            AgingReportParams(page_size=101)


class TestTripProfitabilityParams:
    def test_defaults(self) -> None:
        params = TripProfitabilityParams()
        assert params.boat_id is None
        assert params.from_date is None
        assert params.to_date is None
        assert params.profitability is None
        assert params.q is None
        assert params.page == 1
        assert params.page_size == 20

    def test_accepts_boat_id(self) -> None:
        boat_id = uuid.uuid4()
        params = TripProfitabilityParams(boat_id=boat_id)
        assert params.boat_id == boat_id

    def test_accepts_profitability_values(self) -> None:
        assert (
            TripProfitabilityParams(profitability="profitable").profitability
            == ProfitabilityFilter.PROFITABLE
        )
        assert (
            TripProfitabilityParams(profitability="loss").profitability == ProfitabilityFilter.LOSS
        )

    def test_rejects_invalid_profitability(self) -> None:
        with pytest.raises(ValidationError):
            TripProfitabilityParams(profitability="break-even")

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            TripProfitabilityParams(from_date=date(2026, 7, 31), to_date=date(2026, 7, 1))

    def test_accepts_equal_from_and_to_date(self) -> None:
        params = TripProfitabilityParams(from_date=date(2026, 7, 1), to_date=date(2026, 7, 1))
        assert params.from_date == params.to_date

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            TripProfitabilityParams(page=0)

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            TripProfitabilityParams(page_size=101)

    def test_has_no_status_field(self) -> None:
        """Confirmed design decision: since only `returned` trips are ever
        eligible (a hard invariant, not a toggle), a status filter would be
        a no-op or force zero rows, so it is not exposed."""
        assert "status" not in TripProfitabilityParams.model_fields

    def test_has_no_sort_field(self) -> None:
        assert "sort" not in TripProfitabilityParams.model_fields


class TestBoatProfitabilityParams:
    def test_defaults(self) -> None:
        params = BoatProfitabilityParams()
        assert params.boat_id is None
        assert params.from_date is None
        assert params.to_date is None
        assert params.min_trips is None
        assert params.profitability is None
        assert params.q is None
        assert params.page == 1
        assert params.page_size == 20

    def test_accepts_min_trips(self) -> None:
        params = BoatProfitabilityParams(min_trips=5)
        assert params.min_trips == 5

    def test_rejects_min_trips_below_one(self) -> None:
        with pytest.raises(ValidationError):
            BoatProfitabilityParams(min_trips=0)

    def test_accepts_profitability_values(self) -> None:
        assert (
            BoatProfitabilityParams(profitability="profitable").profitability
            == ProfitabilityFilter.PROFITABLE
        )
        assert (
            BoatProfitabilityParams(profitability="loss").profitability == ProfitabilityFilter.LOSS
        )

    def test_rejects_invalid_profitability(self) -> None:
        with pytest.raises(ValidationError):
            BoatProfitabilityParams(profitability="break-even")

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            BoatProfitabilityParams(from_date=date(2026, 7, 31), to_date=date(2026, 7, 1))

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            BoatProfitabilityParams(page_size=101)

    def test_has_no_sort_field(self) -> None:
        assert "sort" not in BoatProfitabilityParams.model_fields


class TestFishSalesParams:
    def test_defaults(self) -> None:
        params = FishSalesParams()
        assert params.fish_id is None
        assert params.from_date is None
        assert params.to_date is None
        assert params.customer_id is None
        assert params.boat_id is None
        assert params.trip_id is None
        assert params.min_quantity is None
        assert params.min_revenue is None
        assert params.q is None
        assert params.page == 1
        assert params.page_size == 20

    def test_accepts_entity_filters(self) -> None:
        fish_id, customer_id, boat_id, trip_id = (
            uuid.uuid4(),
            uuid.uuid4(),
            uuid.uuid4(),
            uuid.uuid4(),
        )
        params = FishSalesParams(
            fish_id=fish_id, customer_id=customer_id, boat_id=boat_id, trip_id=trip_id
        )
        assert params.fish_id == fish_id
        assert params.customer_id == customer_id
        assert params.boat_id == boat_id
        assert params.trip_id == trip_id

    def test_accepts_min_quantity_and_min_revenue(self) -> None:
        params = FishSalesParams(min_quantity="10.5", min_revenue="1000.00")
        assert params.min_quantity == Decimal("10.5")
        assert params.min_revenue == Decimal("1000.00")

    def test_rejects_negative_min_quantity(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesParams(min_quantity="-1")

    def test_rejects_negative_min_revenue(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesParams(min_revenue="-1")

    def test_rejects_from_date_after_to_date(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesParams(from_date=date(2026, 7, 31), to_date=date(2026, 7, 1))

    def test_accepts_equal_from_and_to_date(self) -> None:
        params = FishSalesParams(from_date=date(2026, 7, 1), to_date=date(2026, 7, 1))
        assert params.from_date == params.to_date

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesParams(page=0)

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesParams(page_size=101)

    def test_has_no_sort_field(self) -> None:
        assert "sort" not in FishSalesParams.model_fields


class TestFishSalesHistoryParams:
    def test_requires_fish_id(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesHistoryParams()

    def test_rejects_invalid_fish_id(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesHistoryParams(fish_id="not-a-uuid")

    def test_defaults(self) -> None:
        fish_id = uuid.uuid4()
        params = FishSalesHistoryParams(fish_id=fish_id)
        assert params.fish_id == fish_id
        assert params.page == 1
        assert params.page_size == 20

    def test_rejects_page_below_one(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesHistoryParams(fish_id=uuid.uuid4(), page=0)

    def test_rejects_page_size_above_one_hundred(self) -> None:
        with pytest.raises(ValidationError):
            FishSalesHistoryParams(fish_id=uuid.uuid4(), page_size=101)

    def test_has_no_sort_field(self) -> None:
        assert "sort" not in FishSalesHistoryParams.model_fields
