import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.core.errors import ConflictError
from app.modules.companies.constants import CompanyStatus
from app.modules.companies.exceptions import CompanyNotFoundError
from app.modules.fish.exceptions import FishNotFoundError
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.exceptions import (
    InvoiceCalculationError,
    InvoiceCompanyInactiveError,
    InvoiceCompanyNotFoundError,
    InvoiceEmptyError,
    InvoiceInsufficientInventoryError,
    InvoiceItemFishMismatchError,
    InvoiceItemFishNotFoundError,
    InvoiceItemQuantityExceedsAvailableError,
    InvoiceItemTripCatchNotFoundError,
    InvoiceNotDraftError,
    InvoiceNotFoundError,
    InvoiceNumberConflictError,
)
from app.modules.invoices.models import Invoice, InvoiceItem, InvoiceSequence
from app.modules.invoices.schemas import InvoiceListParams
from app.modules.invoices.service import InvoiceService
from app.modules.trip_catches.exceptions import (
    TripCatchInsufficientQuantityError,
    TripCatchNotFoundError,
)


class _FakeConstraintCause(Exception):
    """`__cause__` must be a BaseException, so this stands in for the part of
    asyncpg's UniqueViolationError that _translate_integrity_error reads."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("fake constraint violation")
        self.constraint_name = constraint_name


class _FakeDriverError(Exception):
    """Stands in for asyncpg's UniqueViolationError, chained as __cause__."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("duplicate key value violates unique constraint")
        self.__cause__ = _FakeConstraintCause(constraint_name)


class _FakeIntegrityError(Exception):
    """Stands in for sqlalchemy.exc.IntegrityError - only `.orig` is read."""

    def __init__(self, constraint_name: str) -> None:
        super().__init__("integrity error")
        self.orig = _FakeDriverError(constraint_name)


class _CompanyStub:
    """Stands in for a CompanyResponse - only .id/.status are read by
    InvoiceService."""

    def __init__(
        self, company_id: uuid.UUID | None = None, *, status: CompanyStatus = CompanyStatus.ACTIVE
    ) -> None:
        self.id = company_id or uuid.uuid4()
        self.status = status


class _FakeCompanyService:
    """Stands in for CompanyService.get/find_ids_by_name - the two entry
    points InvoiceService calls (ARCHITECTURE.md §2 - cross-module access
    goes through the other module's service, never its repository)."""

    def __init__(self, *, company: _CompanyStub | None = None, raises: bool = False) -> None:
        self.company = company
        self.raises = raises
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.find_ids_calls: list[tuple[uuid.UUID, str]] = []
        self.find_ids_result: list[uuid.UUID] = []

    async def get(self, company_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _CompanyStub:
        self.get_calls.append((company_id, tenant_id))
        if self.raises:
            raise CompanyNotFoundError("Company not found")
        assert self.company is not None
        return self.company

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        self.find_ids_calls.append((tenant_id, q))
        return self.find_ids_result


class _TripCatchStub:
    """Stands in for a TripCatchResponse - only .fish_id/.available_quantity
    are read by InvoiceService."""

    def __init__(
        self,
        trip_catch_id: uuid.UUID | None = None,
        *,
        fish_id: uuid.UUID | None = None,
        available_quantity: Decimal = Decimal("100.000"),
    ) -> None:
        self.id = trip_catch_id or uuid.uuid4()
        self.fish_id = fish_id or uuid.uuid4()
        self.available_quantity = available_quantity


class _FakeTripCatchService:
    """Stands in for TripCatchService.get - the only entry point
    InvoiceService calls (ARCHITECTURE.md §2 - cross-module access goes
    through the other module's service, never its repository)."""

    def __init__(self, *, trip_catch: _TripCatchStub | None = None, raises: bool = False) -> None:
        self.trip_catch = trip_catch
        self.raises = raises
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def get(self, trip_catch_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _TripCatchStub:
        self.get_calls.append((trip_catch_id, tenant_id))
        if self.raises:
            raise TripCatchNotFoundError("Trip catch not found")
        assert self.trip_catch is not None
        return self.trip_catch


class _FakeIssueTripCatchService:
    """Stands in for TripCatchService.deduct_available_quantity - the only
    entry point InvoiceService.issue calls on it."""

    def __init__(self, *, raises: Exception | None = None) -> None:
        self.raises = raises
        self.deduct_calls: list[tuple[uuid.UUID, Decimal, uuid.UUID, uuid.UUID]] = []

    async def deduct_available_quantity(
        self,
        trip_catch_id: uuid.UUID,
        quantity: Decimal,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> object:
        self.deduct_calls.append((trip_catch_id, quantity, tenant_id, actor_id))
        if self.raises is not None:
            raise self.raises
        return object()


class _FakeFishService:
    """Stands in for FishService.get/find_ids_by_name - the two entry
    points InvoiceService calls."""

    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises
        self.get_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        self.find_ids_calls: list[tuple[uuid.UUID, str]] = []
        self.find_ids_result: list[uuid.UUID] = []

    async def get(self, fish_id: uuid.UUID, *, tenant_id: uuid.UUID) -> object:
        self.get_calls.append((fish_id, tenant_id))
        if self.raises:
            raise FishNotFoundError("Fish not found")
        return object()

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        self.find_ids_calls.append((tenant_id, q))
        return self.find_ids_result


class _FakeInvoiceRepo:
    def __init__(self, rows: list[Invoice] | None = None, total: int = 0) -> None:
        self.rows = rows or []
        self.total = total
        self.last_search_call: dict[str, Any] | None = None
        # invoice_id -> items, consumed by _recalculate_invoice via search_items.
        self.items_by_invoice: dict[uuid.UUID, list[InvoiceItem]] = {}
        # For issue()'s locked lookup - distinct from get_by_id (Sessions 2-4).
        self.locked_invoice: Invoice | None = None
        self.get_for_update_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        # For _allocate_invoice_number.
        self.sequences: dict[tuple[uuid.UUID, str, str], InvoiceSequence] = {}
        self.ensure_sequence_calls: list[tuple[uuid.UUID, str, str]] = []

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Invoice], int]:
        self.last_search_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total

    async def search_items(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID, **kwargs: Any
    ) -> list[InvoiceItem]:
        return self.items_by_invoice.get(invoice_id, [])

    async def get_by_id_for_update(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Invoice | None:
        self.get_for_update_calls.append((invoice_id, tenant_id))
        return self.locked_invoice

    async def ensure_sequence_row(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> None:
        self.ensure_sequence_calls.append((tenant_id, prefix, fiscal_year))
        key = (tenant_id, prefix, fiscal_year)
        if key not in self.sequences:
            self.sequences[key] = InvoiceSequence(
                tenant_id=tenant_id, prefix=prefix, fiscal_year=fiscal_year, last_number=0
            )

    async def get_sequence_for_update(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> InvoiceSequence:
        return self.sequences[(tenant_id, prefix, fiscal_year)]


def _make_invoice(**overrides: Any) -> Invoice:
    """An Invoice that satisfies InvoiceResponse validation without touching
    the DB - the non-nullable columns normally filled by server_default /
    TimestampMixin need explicit values since this object is never flushed."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "invoice_number": None,
        "invoice_date": date(2026, 7, 22),
        "status": InvoiceStatus.DRAFT,
        "subtotal": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "transport_charge": Decimal("0"),
        "other_charge": Decimal("0"),
        "round_off": Decimal("0"),
        "total_amount": Decimal("0"),
        "paid_amount": Decimal("0"),
        "balance_amount": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Invoice(**defaults)


def _make_invoice_item(**overrides: Any) -> InvoiceItem:
    """An InvoiceItem that satisfies InvoiceItemResponse validation without
    touching the DB - see _make_invoice's docstring for why explicit values
    are needed for columns normally filled by server_default/TimestampMixin."""
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "invoice_id": uuid.uuid4(),
        "line_number": 1,
        "fish_id": uuid.uuid4(),
        "trip_catch_id": uuid.uuid4(),
        "quantity": Decimal("1"),
        "unit": "kg",
        "rate": Decimal("1"),
        "discount_percent": Decimal("0"),
        "discount_amount": Decimal("0"),
        "taxable_amount": Decimal("0"),
        "tax_rate": Decimal("0"),
        "tax_amount": Decimal("0"),
        "line_total": Decimal("0"),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return InvoiceItem(**defaults)


def _service_with_fakes(
    rows: list[Invoice] | None = None,
    total: int = 0,
    *,
    company: _CompanyStub | None = None,
    company_raises: bool = False,
) -> tuple[InvoiceService, _FakeInvoiceRepo, _FakeCompanyService]:
    service = InvoiceService.__new__(InvoiceService)
    fake_repo = _FakeInvoiceRepo(rows, total)
    fake_company_service = _FakeCompanyService(company=company, raises=company_raises)
    service._repo = fake_repo  # type: ignore[assignment]
    service._company_service = fake_company_service  # type: ignore[assignment]
    return service, fake_repo, fake_company_service


class _FakeSession:
    """Stands in for AsyncSession - issue() only ever calls .rollback() on
    it along the validation-failure paths these unit tests cover (the
    session-touching happy path is integration-tested instead)."""

    def __init__(self) -> None:
        self.rollback_calls = 0

    async def rollback(self) -> None:
        self.rollback_calls += 1


def _issue_service_with_fakes(
    *,
    invoice: Invoice | None,
    items: list[InvoiceItem] | None = None,
    company: _CompanyStub | None = None,
    company_raises: bool = False,
    trip_catch_raises: Exception | None = None,
) -> tuple[
    InvoiceService, _FakeInvoiceRepo, _FakeCompanyService, _FakeIssueTripCatchService, _FakeSession
]:
    """Wires only the collaborators issue() touches before it would need a
    real database session (get_by_id_for_update, search_items,
    _ensure_company_active, _recalculate_invoice, and the trip catch
    deduction loop up to the point a fake raises), plus a fake session that
    only supports .rollback() - sufficient for the validation-failure paths
    unit tests cover. The happy path (session flush/commit/refresh, real
    locking) is integration-tested instead."""
    service = InvoiceService.__new__(InvoiceService)
    fake_repo = _FakeInvoiceRepo()
    fake_repo.locked_invoice = invoice
    if invoice is not None:
        fake_repo.items_by_invoice[invoice.id] = items if items is not None else []
    fake_company_service = _FakeCompanyService(company=company, raises=company_raises)
    fake_trip_catch_service = _FakeIssueTripCatchService(raises=trip_catch_raises)
    fake_session = _FakeSession()
    service._repo = fake_repo  # type: ignore[assignment]
    service._company_service = fake_company_service  # type: ignore[assignment]
    service._trip_catch_service = fake_trip_catch_service  # type: ignore[assignment]
    service._session = fake_session  # type: ignore[assignment]
    return service, fake_repo, fake_company_service, fake_trip_catch_service, fake_session


def _service_with_item_fakes(
    *,
    trip_catch: _TripCatchStub | None = None,
    trip_catch_raises: bool = False,
    fish_raises: bool = False,
) -> tuple[InvoiceService, _FakeTripCatchService, _FakeFishService]:
    service = InvoiceService.__new__(InvoiceService)
    fake_trip_catch_service = _FakeTripCatchService(trip_catch=trip_catch, raises=trip_catch_raises)
    fake_fish_service = _FakeFishService(raises=fish_raises)
    service._trip_catch_service = fake_trip_catch_service  # type: ignore[assignment]
    service._fish_service = fake_fish_service  # type: ignore[assignment]
    return service, fake_trip_catch_service, fake_fish_service


class TestEnsureCompanyActive:
    async def test_returns_company_when_active(self) -> None:
        company = _CompanyStub(status=CompanyStatus.ACTIVE)
        service, _, _ = _service_with_fakes(company=company)

        result = await service._ensure_company_active(company.id, uuid.uuid4())

        assert result is company  # type: ignore[comparison-overlap]

    async def test_raises_not_found_when_company_missing(self) -> None:
        service, _, _ = _service_with_fakes(company_raises=True)

        with pytest.raises(InvoiceCompanyNotFoundError):
            await service._ensure_company_active(uuid.uuid4(), uuid.uuid4())

    async def test_raises_inactive_when_company_not_active(self) -> None:
        company = _CompanyStub(status=CompanyStatus.INACTIVE)
        service, _, _ = _service_with_fakes(company=company)

        with pytest.raises(InvoiceCompanyInactiveError):
            await service._ensure_company_active(company.id, uuid.uuid4())

    async def test_tenant_scoping_is_forwarded_to_company_service(self) -> None:
        company = _CompanyStub(status=CompanyStatus.ACTIVE)
        service, _, fake_company_service = _service_with_fakes(company=company)
        tenant_id = uuid.uuid4()

        await service._ensure_company_active(company.id, tenant_id)

        assert fake_company_service.get_calls == [(company.id, tenant_id)]


class TestEnsureDraft:
    def test_draft_invoice_does_not_raise(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        InvoiceService._ensure_draft(invoice)

    @pytest.mark.parametrize(
        "status",
        [
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
            InvoiceStatus.PAID,
            InvoiceStatus.CANCELLED,
        ],
    )
    def test_non_draft_invoice_raises(self, status: InvoiceStatus) -> None:
        invoice = _make_invoice(status=status)
        with pytest.raises(InvoiceNotDraftError):
            InvoiceService._ensure_draft(invoice)


class TestTranslateIntegrityError:
    def test_invoice_number_unique_constraint_maps_to_number_conflict_error(self) -> None:
        """Defensive backstop - _allocate_invoice_number's FOR UPDATE
        locking should make this unreachable in normal operation, but the
        constraint firing must still surface a clean 409, not a raw 500."""
        exc = _FakeIntegrityError("ix_invoices_tenant_invoice_number")
        result = InvoiceService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert isinstance(result, InvoiceNumberConflictError)

    def test_unknown_constraint_falls_back_to_generic_conflict(self) -> None:
        exc = _FakeIntegrityError("some_other_constraint")
        result = InvoiceService._translate_integrity_error(exc)  # type: ignore[arg-type]
        assert type(result) is ConflictError

    def test_missing_orig_falls_back_to_generic_conflict(self) -> None:
        class _BareError(Exception):
            orig = None

        result = InvoiceService._translate_integrity_error(_BareError())  # type: ignore[arg-type]
        assert type(result) is ConflictError


class TestListInvoicesPaginationMath:
    async def test_first_page_of_several(self) -> None:
        rows = [_make_invoice() for _ in range(2)]
        service, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_invoices(
            tenant_id=uuid.uuid4(), params=InvoiceListParams(page=1, page_size=2)
        )

        assert len(result.data) == 2
        assert result.meta.total_records == 5
        assert result.meta.total_pages == 3
        assert result.meta.current_page == 1
        assert result.meta.has_previous is False
        assert result.meta.has_next is True

    async def test_last_page_has_no_next(self) -> None:
        rows = [_make_invoice()]
        service, _, _ = _service_with_fakes(rows, total=5)

        result = await service.list_invoices(
            tenant_id=uuid.uuid4(), params=InvoiceListParams(page=3, page_size=2)
        )

        assert result.meta.has_next is False
        assert result.meta.has_previous is True

    async def test_empty_result_gives_zero_pages(self) -> None:
        service, _, _ = _service_with_fakes([], total=0)

        result = await service.list_invoices(
            tenant_id=uuid.uuid4(), params=InvoiceListParams(page=1, page_size=20)
        )

        assert result.data == []
        assert result.meta.total_records == 0
        assert result.meta.total_pages == 0
        assert result.meta.has_next is False
        assert result.meta.has_previous is False

    async def test_filters_are_forwarded_to_the_repository(self) -> None:
        service, fake_repo, fake_company_service = _service_with_fakes([], total=0)
        tenant_id = uuid.uuid4()
        company_id = uuid.uuid4()

        await service.list_invoices(
            tenant_id=tenant_id,
            params=InvoiceListParams(
                company_id=company_id,
                status=InvoiceStatus.DRAFT,
                invoice_date_from="2026-07-01",
                invoice_date_to="2026-07-31",
                sort="-invoice_date",
                page=2,
                page_size=10,
            ),
        )

        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["tenant_id"] == tenant_id
        assert fake_repo.last_search_call["company_id"] == company_id
        assert fake_repo.last_search_call["status"] == InvoiceStatus.DRAFT
        assert fake_repo.last_search_call["sort"] == "-invoice_date"
        assert fake_repo.last_search_call["page"] == 2
        assert fake_repo.last_search_call["page_size"] == 10
        assert fake_repo.last_search_call["q_company_ids"] is None
        assert fake_company_service.find_ids_calls == []

    async def test_q_triggers_company_name_lookup_and_forwards_ids(self) -> None:
        matched_company_id = uuid.uuid4()
        service, fake_repo, fake_company_service = _service_with_fakes([], total=0)
        fake_company_service.find_ids_result = [matched_company_id]
        tenant_id = uuid.uuid4()

        await service.list_invoices(tenant_id=tenant_id, params=InvoiceListParams(q="Ocean"))

        assert fake_company_service.find_ids_calls == [(tenant_id, "Ocean")]
        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["q_company_ids"] == [matched_company_id]

    async def test_blank_q_does_not_trigger_company_name_lookup(self) -> None:
        service, fake_repo, fake_company_service = _service_with_fakes([], total=0)

        await service.list_invoices(tenant_id=uuid.uuid4(), params=InvoiceListParams(q="   "))

        assert fake_company_service.find_ids_calls == []
        assert fake_repo.last_search_call is not None
        assert fake_repo.last_search_call["q_company_ids"] is None


class TestEnsureTripCatchAndFishValid:
    async def test_passes_through_for_a_matching_trip_catch_within_availability(self) -> None:
        fish_id = uuid.uuid4()
        trip_catch = _TripCatchStub(fish_id=fish_id, available_quantity=Decimal("100.000"))
        service, _, _ = _service_with_item_fakes(trip_catch=trip_catch)

        result = await service._ensure_trip_catch_and_fish_valid(
            trip_catch.id, fish_id, Decimal("50.000"), tenant_id=uuid.uuid4()
        )

        assert result is trip_catch  # type: ignore[comparison-overlap]

    async def test_quantity_equal_to_available_is_allowed(self) -> None:
        fish_id = uuid.uuid4()
        trip_catch = _TripCatchStub(fish_id=fish_id, available_quantity=Decimal("50.000"))
        service, _, _ = _service_with_item_fakes(trip_catch=trip_catch)

        await service._ensure_trip_catch_and_fish_valid(
            trip_catch.id, fish_id, Decimal("50.000"), tenant_id=uuid.uuid4()
        )

    async def test_raises_trip_catch_not_found_when_trip_catch_missing(self) -> None:
        service, _, _ = _service_with_item_fakes(trip_catch_raises=True)

        with pytest.raises(InvoiceItemTripCatchNotFoundError):
            await service._ensure_trip_catch_and_fish_valid(
                uuid.uuid4(), uuid.uuid4(), Decimal("10.000"), tenant_id=uuid.uuid4()
            )

    async def test_raises_fish_not_found_when_fish_missing(self) -> None:
        trip_catch = _TripCatchStub()
        service, _, _ = _service_with_item_fakes(trip_catch=trip_catch, fish_raises=True)

        with pytest.raises(InvoiceItemFishNotFoundError):
            await service._ensure_trip_catch_and_fish_valid(
                trip_catch.id, uuid.uuid4(), Decimal("10.000"), tenant_id=uuid.uuid4()
            )

    async def test_raises_fish_mismatch_when_fish_id_differs_from_trip_catch(self) -> None:
        trip_catch = _TripCatchStub(fish_id=uuid.uuid4())
        service, _, _ = _service_with_item_fakes(trip_catch=trip_catch)

        with pytest.raises(InvoiceItemFishMismatchError):
            await service._ensure_trip_catch_and_fish_valid(
                trip_catch.id, uuid.uuid4(), Decimal("10.000"), tenant_id=uuid.uuid4()
            )

    async def test_raises_quantity_exceeds_available_when_over_the_limit(self) -> None:
        fish_id = uuid.uuid4()
        trip_catch = _TripCatchStub(fish_id=fish_id, available_quantity=Decimal("10.000"))
        service, _, _ = _service_with_item_fakes(trip_catch=trip_catch)

        with pytest.raises(InvoiceItemQuantityExceedsAvailableError):
            await service._ensure_trip_catch_and_fish_valid(
                trip_catch.id, fish_id, Decimal("10.001"), tenant_id=uuid.uuid4()
            )

    async def test_tenant_scoping_is_forwarded_to_both_services(self) -> None:
        fish_id = uuid.uuid4()
        trip_catch = _TripCatchStub(fish_id=fish_id)
        service, fake_trip_catch_service, fake_fish_service = _service_with_item_fakes(
            trip_catch=trip_catch
        )
        tenant_id = uuid.uuid4()

        await service._ensure_trip_catch_and_fish_valid(
            trip_catch.id, fish_id, Decimal("1.000"), tenant_id=tenant_id
        )

        assert fake_trip_catch_service.get_calls == [(trip_catch.id, tenant_id)]
        assert fake_fish_service.get_calls == [(fish_id, tenant_id)]

    async def test_fish_existence_is_checked_before_mismatch(self) -> None:
        """Fish existence must be validated even when it would also fail the
        mismatch check - a client shouldn't learn "mismatch" about a fish_id
        that doesn't exist at all."""
        trip_catch = _TripCatchStub(fish_id=uuid.uuid4())
        service, _, _ = _service_with_item_fakes(trip_catch=trip_catch, fish_raises=True)

        with pytest.raises(InvoiceItemFishNotFoundError):
            await service._ensure_trip_catch_and_fish_valid(
                trip_catch.id, uuid.uuid4(), Decimal("1.000"), tenant_id=uuid.uuid4()
            )


class TestRecalculateInvoice:
    async def test_no_items_zeroes_calculated_fields_but_keeps_charges(self) -> None:
        invoice = _make_invoice(transport_charge=Decimal("250.00"), other_charge=Decimal("10.00"))
        service, fake_repo, _ = _service_with_fakes()
        fake_repo.items_by_invoice[invoice.id] = []

        await service._recalculate_invoice(invoice, invoice.tenant_id)

        assert invoice.subtotal == Decimal("0.00")
        assert invoice.discount_amount == Decimal("0.00")
        assert invoice.taxable_amount == Decimal("0.00")
        assert invoice.tax_amount == Decimal("0.00")
        assert invoice.total_amount == Decimal("260.00")
        assert invoice.balance_amount == Decimal("260.00")

    async def test_updates_item_fields_and_invoice_aggregates(self) -> None:
        invoice = _make_invoice()
        item = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            quantity=Decimal("50.000"),
            rate=Decimal("450.0000"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("5.00"),
        )
        service, fake_repo, _ = _service_with_fakes()
        fake_repo.items_by_invoice[invoice.id] = [item]

        await service._recalculate_invoice(invoice, invoice.tenant_id)

        assert item.discount_amount == Decimal("0.00")
        assert item.taxable_amount == Decimal("22500.00")
        assert item.tax_amount == Decimal("1125.00")
        assert item.line_total == Decimal("23625.00")
        assert invoice.subtotal == Decimal("23625.00")
        assert invoice.taxable_amount == Decimal("22500.00")
        assert invoice.tax_amount == Decimal("1125.00")
        assert invoice.total_amount == Decimal("23625.00")
        assert invoice.balance_amount == Decimal("23625.00")

    async def test_sums_across_multiple_items(self) -> None:
        invoice = _make_invoice(transport_charge=Decimal("100.00"))
        item_a = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            line_number=1,
            quantity=Decimal("10"),
            rate=Decimal("100"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        item_b = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            line_number=2,
            quantity=Decimal("5"),
            rate=Decimal("50"),
            discount_percent=Decimal("10"),
            tax_rate=Decimal("0"),
        )
        service, fake_repo, _ = _service_with_fakes()
        fake_repo.items_by_invoice[invoice.id] = [item_a, item_b]

        await service._recalculate_invoice(invoice, invoice.tenant_id)

        # item_a: 10*100=1000, item_b: 5*50=250, discount 25 -> taxable 225
        assert invoice.subtotal == Decimal("1225.00")
        assert invoice.discount_amount == Decimal("25.00")
        assert invoice.total_amount == Decimal("1325.00")

    async def test_deleted_items_are_not_read_by_recalculation(self) -> None:
        """search_items already excludes soft-deleted rows (repository-level
        contract) - this asserts the service doesn't try to work around
        that by reading the repo's full item list some other way."""
        invoice = _make_invoice()
        service, fake_repo, _ = _service_with_fakes()
        fake_repo.items_by_invoice[invoice.id] = []  # simulates all-deleted

        await service._recalculate_invoice(invoice, invoice.tenant_id)

        assert invoice.subtotal == Decimal("0.00")
        assert invoice.total_amount == Decimal("0.00")

    async def test_translates_financial_calculation_error(self) -> None:
        """A value that bypasses the request schema (e.g. a negative rate,
        never reachable through the API) must surface as the app's own
        InvoiceCalculationError, never a raw domain ValueError."""
        invoice = _make_invoice()
        item = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            quantity=Decimal("10"),
            rate=Decimal("-5"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("0"),
        )
        service, fake_repo, _ = _service_with_fakes()
        fake_repo.items_by_invoice[invoice.id] = [item]

        with pytest.raises(InvoiceCalculationError):
            await service._recalculate_invoice(invoice, invoice.tenant_id)


class TestIssueValidation:
    """Unit-level coverage for issue()'s validation steps that raise before
    any real database session interaction is needed (not-found, not-draft,
    empty invoice, company checks, and the trip catch deduction loop up to
    the point a fake collaborator raises). The full happy path - session
    flush/commit/refresh, real FOR UPDATE locking, actual invoice numbering
    - is integration-tested against a real database instead
    (tests/integration/test_invoice_issue.py)."""

    async def test_raises_not_found_when_invoice_missing(self) -> None:
        service, fake_repo, _, _, fake_session = _issue_service_with_fakes(invoice=None)
        invoice_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        with pytest.raises(InvoiceNotFoundError):
            await service.issue(invoice_id, tenant_id=tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.get_for_update_calls == [(invoice_id, tenant_id)]
        assert fake_session.rollback_calls == 1

    @pytest.mark.parametrize(
        "status",
        [
            InvoiceStatus.ISSUED,
            InvoiceStatus.PARTIALLY_PAID,
            InvoiceStatus.PAID,
            InvoiceStatus.CANCELLED,
        ],
    )
    async def test_raises_not_draft_for_non_draft_statuses(self, status: InvoiceStatus) -> None:
        """Covers "cannot issue twice" (ISSUED/PARTIALLY_PAID/PAID) and
        "cannot issue a cancelled invoice" (CANCELLED) with the same guard."""
        invoice = _make_invoice(status=status)
        service, _, _, _, _ = _issue_service_with_fakes(invoice=invoice)

        with pytest.raises(InvoiceNotDraftError):
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

    async def test_raises_empty_when_no_active_items(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        service, _, _, _, _ = _issue_service_with_fakes(invoice=invoice, items=[])

        with pytest.raises(InvoiceEmptyError):
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

    async def test_raises_company_not_found_when_company_missing(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        item = _make_invoice_item(invoice_id=invoice.id, tenant_id=invoice.tenant_id)
        service, _, _, _, _ = _issue_service_with_fakes(
            invoice=invoice, items=[item], company_raises=True
        )

        with pytest.raises(InvoiceCompanyNotFoundError):
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

    async def test_raises_company_inactive_when_company_not_active(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        item = _make_invoice_item(invoice_id=invoice.id, tenant_id=invoice.tenant_id)
        company = _CompanyStub(company_id=invoice.company_id, status=CompanyStatus.INACTIVE)
        service, _, _, _, _ = _issue_service_with_fakes(
            invoice=invoice, items=[item], company=company
        )

        with pytest.raises(InvoiceCompanyInactiveError):
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

    async def test_raises_insufficient_inventory_when_trip_catch_service_rejects(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        item = _make_invoice_item(invoice_id=invoice.id, tenant_id=invoice.tenant_id)
        company = _CompanyStub(company_id=invoice.company_id, status=CompanyStatus.ACTIVE)
        service, _, _, fake_trip_catch_service, fake_session = _issue_service_with_fakes(
            invoice=invoice,
            items=[item],
            company=company,
            trip_catch_raises=TripCatchInsufficientQuantityError("not enough"),
        )

        with pytest.raises(InvoiceInsufficientInventoryError):
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

        assert fake_trip_catch_service.deduct_calls  # the loop actually ran
        assert fake_session.rollback_calls == 1

    async def test_translates_trip_catch_not_found_during_deduction(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        item = _make_invoice_item(invoice_id=invoice.id, tenant_id=invoice.tenant_id)
        company = _CompanyStub(company_id=invoice.company_id, status=CompanyStatus.ACTIVE)
        service, _, _, _, _ = _issue_service_with_fakes(
            invoice=invoice,
            items=[item],
            company=company,
            trip_catch_raises=TripCatchNotFoundError("gone"),
        )

        with pytest.raises(InvoiceItemTripCatchNotFoundError):
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

    async def test_raises_trip_catch_not_found_when_item_has_no_trip_catch_id(self) -> None:
        """Defends the nullable-at-the-DB-level trip_catch_id column even
        though the request schema currently requires it at item creation -
        the column being nullable at all (ARCHITECTURE.md §16.1) means this
        must fail cleanly, not with an AttributeError/None-deduction, if
        that invariant were ever violated."""
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        item = _make_invoice_item(
            invoice_id=invoice.id, tenant_id=invoice.tenant_id, trip_catch_id=None
        )
        company = _CompanyStub(company_id=invoice.company_id, status=CompanyStatus.ACTIVE)
        service, _, _, fake_trip_catch_service, _ = _issue_service_with_fakes(
            invoice=invoice, items=[item], company=company
        )

        with pytest.raises(InvoiceItemTripCatchNotFoundError):
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

        assert fake_trip_catch_service.deduct_calls == []

    async def test_locked_lookup_is_scoped_to_the_given_tenant(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.ISSUED)
        service, fake_repo, _, _, _ = _issue_service_with_fakes(invoice=invoice)
        tenant_id = uuid.uuid4()

        with pytest.raises(InvoiceNotDraftError):
            await service.issue(invoice.id, tenant_id=tenant_id, actor_id=uuid.uuid4())

        assert fake_repo.get_for_update_calls == [(invoice.id, tenant_id)]

    async def test_rolls_back_the_session_on_any_failure(self) -> None:
        """TASKS.md: "Rollback everything if any step fails" - made
        explicit in issue() rather than relying on the request-scoped
        session's eventual close() to discard unflushed writes."""
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        service, _, _, _, fake_session = _issue_service_with_fakes(invoice=invoice, items=[])

        with pytest.raises(InvoiceEmptyError):
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

        assert fake_session.rollback_calls == 1


class TestAllocateInvoiceNumber:
    """InvoiceService._allocate_invoice_number - the counter-orchestration
    logic (fiscal year computation, ensure-then-lock, increment). The actual
    concurrency guarantee (SELECT ... FOR UPDATE serializing two real
    transactions) can only be verified against a real database - see
    tests/integration/test_invoice_issue.py."""

    async def test_first_allocation_for_a_fiscal_year_starts_at_one(self) -> None:
        service = InvoiceService.__new__(InvoiceService)
        fake_repo = _FakeInvoiceRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        invoice = _make_invoice(invoice_date=date(2026, 7, 22))

        number = await service._allocate_invoice_number(invoice, uuid.uuid4())

        assert number == "INV/2026-27/00001"

    async def test_second_allocation_for_the_same_fiscal_year_increments(self) -> None:
        service = InvoiceService.__new__(InvoiceService)
        fake_repo = _FakeInvoiceRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        invoice = _make_invoice(invoice_date=date(2026, 7, 22))
        tenant_id = uuid.uuid4()

        await service._allocate_invoice_number(invoice, tenant_id)
        second = await service._allocate_invoice_number(invoice, tenant_id)

        assert second == "INV/2026-27/00002"

    async def test_different_fiscal_years_get_independent_counters(self) -> None:
        service = InvoiceService.__new__(InvoiceService)
        fake_repo = _FakeInvoiceRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        tenant_id = uuid.uuid4()
        early_fy = _make_invoice(invoice_date=date(2026, 3, 15))  # FY 2025-26
        late_fy = _make_invoice(invoice_date=date(2026, 7, 22))  # FY 2026-27

        early_number = await service._allocate_invoice_number(early_fy, tenant_id)
        late_number = await service._allocate_invoice_number(late_fy, tenant_id)

        assert early_number == "INV/2025-26/00001"
        assert late_number == "INV/2026-27/00001"

    async def test_different_tenants_get_independent_counters(self) -> None:
        service = InvoiceService.__new__(InvoiceService)
        fake_repo = _FakeInvoiceRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        invoice = _make_invoice(invoice_date=date(2026, 7, 22))

        first_tenant_number = await service._allocate_invoice_number(invoice, uuid.uuid4())
        second_tenant_number = await service._allocate_invoice_number(invoice, uuid.uuid4())

        assert first_tenant_number == "INV/2026-27/00001"
        assert second_tenant_number == "INV/2026-27/00001"

    async def test_ensures_sequence_row_before_locking_it(self) -> None:
        service = InvoiceService.__new__(InvoiceService)
        fake_repo = _FakeInvoiceRepo()
        service._repo = fake_repo  # type: ignore[assignment]
        invoice = _make_invoice(invoice_date=date(2026, 7, 22))
        tenant_id = uuid.uuid4()

        await service._allocate_invoice_number(invoice, tenant_id)

        assert fake_repo.ensure_sequence_calls == [(tenant_id, "INV", "2026-27")]
