import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
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
    InvoiceReconciliationError,
)
from app.modules.invoices.models import Invoice, InvoiceItem, InvoiceSequence
from app.modules.invoices.schemas import InvoiceListParams, TripCatchDraftDemandResponse
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
        self.recalculate_outstanding_calls: list[tuple[uuid.UUID, uuid.UUID, Decimal]] = []
        # For get_trip_catch_conflicts (Sprint 15 Session 6).
        self.names_by_id: dict[uuid.UUID, str] = {}
        self.get_names_by_ids_calls: list[tuple[list[uuid.UUID], uuid.UUID]] = []

    async def get(self, company_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _CompanyStub:
        self.get_calls.append((company_id, tenant_id))
        if self.raises:
            raise CompanyNotFoundError("Company not found")
        assert self.company is not None
        return self.company

    async def get_for_update(
        self, company_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> _CompanyStub | None:
        # Stands in for the Sprint 13 Session 3 concurrency fix's row lock -
        # recalculate_payment_totals calls this before summing, but never
        # reads its return value (see CompanyService.get_for_update's
        # docstring), so this fake just records the call.
        self.get_calls.append((company_id, tenant_id))
        return self.company

    async def find_ids_by_name(self, tenant_id: uuid.UUID, q: str) -> list[uuid.UUID]:
        self.find_ids_calls.append((tenant_id, q))
        return self.find_ids_result

    async def recalculate_outstanding(
        self, company_id: uuid.UUID, *, tenant_id: uuid.UUID, total_open_balance: Decimal
    ) -> None:
        self.recalculate_outstanding_calls.append((company_id, tenant_id, total_open_balance))

    async def get_names_by_ids(
        self, company_ids: list[uuid.UUID], *, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        self.get_names_by_ids_calls.append((company_ids, tenant_id))
        return {cid: name for cid, name in self.names_by_id.items() if cid in company_ids}


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
        # For get_issue_preflight (Sprint 15 Session 10).
        self.many_by_id: dict[uuid.UUID, _TripCatchStub] = {}
        self.get_many_by_ids_calls: list[tuple[list[uuid.UUID], uuid.UUID]] = []

    async def get(self, trip_catch_id: uuid.UUID, *, tenant_id: uuid.UUID) -> _TripCatchStub:
        self.get_calls.append((trip_catch_id, tenant_id))
        if self.raises:
            raise TripCatchNotFoundError("Trip catch not found")
        assert self.trip_catch is not None
        return self.trip_catch

    async def get_many_by_ids(
        self, trip_catch_ids: list[uuid.UUID], *, tenant_id: uuid.UUID
    ) -> list[_TripCatchStub]:
        self.get_many_by_ids_calls.append((trip_catch_ids, tenant_id))
        return [self.many_by_id[tc_id] for tc_id in trip_catch_ids if tc_id in self.many_by_id]


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
        # For recalculate_payment_totals (Sprint 10 Session 4).
        self.by_id: dict[uuid.UUID, Invoice] = {}
        self.open_balance_by_company: dict[uuid.UUID, Decimal] = {}
        self.sum_open_balance_calls: list[tuple[uuid.UUID, uuid.UUID]] = []
        # For get_trip_catch_draft_demand (Sprint 15 Session 5).
        self.other_draft_quantity: Decimal = Decimal("0")
        self.sum_other_draft_quantity_calls: list[
            tuple[uuid.UUID, uuid.UUID, uuid.UUID | None]
        ] = []
        # For get_trip_catch_conflicts (Sprint 15 Session 6).
        self.conflicting_rows: list[Any] = []
        self.list_conflicts_calls: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID | None]] = []
        # For get_trip_catch_invoice_usage (Sprint 15 Session 7/8).
        self.usage_rows: list[Any] = []
        self.usage_calls: list[tuple[list[uuid.UUID], uuid.UUID, uuid.UUID | None]] = []

    async def search(self, tenant_id: uuid.UUID, **kwargs: Any) -> tuple[list[Invoice], int]:
        self.last_search_call = {"tenant_id": tenant_id, **kwargs}
        return self.rows, self.total

    async def get_by_id(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> Invoice | None:
        return self.by_id.get(invoice_id)

    async def sum_open_balance_by_company(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Decimal:
        self.sum_open_balance_calls.append((company_id, tenant_id))
        return self.open_balance_by_company.get(company_id, Decimal("0"))

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

    async def sum_other_draft_quantity(
        self,
        trip_catch_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        exclude_invoice_id: uuid.UUID | None,
    ) -> Decimal:
        self.sum_other_draft_quantity_calls.append((trip_catch_id, tenant_id, exclude_invoice_id))
        return self.other_draft_quantity

    async def list_invoices_referencing_trip_catch(
        self,
        trip_catch_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        exclude_invoice_id: uuid.UUID | None,
    ) -> list[Any]:
        self.list_conflicts_calls.append((trip_catch_id, tenant_id, exclude_invoice_id))
        return self.conflicting_rows

    async def get_trip_catch_invoice_usage(
        self,
        trip_catch_ids: list[uuid.UUID],
        tenant_id: uuid.UUID,
        *,
        exclude_invoice_id: uuid.UUID | None = None,
    ) -> list[Any]:
        self.usage_calls.append((trip_catch_ids, tenant_id, exclude_invoice_id))
        return self.usage_rows


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


def _service_with_draft_demand_fakes(
    *,
    trip_catch: _TripCatchStub | None = None,
    trip_catch_raises: bool = False,
    other_draft_quantity: Decimal = Decimal("0"),
) -> tuple[InvoiceService, _FakeInvoiceRepo, _FakeTripCatchService]:
    service = InvoiceService.__new__(InvoiceService)
    fake_repo = _FakeInvoiceRepo()
    fake_repo.other_draft_quantity = other_draft_quantity
    fake_trip_catch_service = _FakeTripCatchService(trip_catch=trip_catch, raises=trip_catch_raises)
    service._repo = fake_repo  # type: ignore[assignment]
    service._trip_catch_service = fake_trip_catch_service  # type: ignore[assignment]
    return service, fake_repo, fake_trip_catch_service


def _service_with_conflict_fakes(
    *,
    trip_catch: _TripCatchStub | None = None,
    trip_catch_raises: bool = False,
    conflicting_rows: list[Any] | None = None,
    names_by_id: dict[uuid.UUID, str] | None = None,
) -> tuple[InvoiceService, _FakeInvoiceRepo, _FakeTripCatchService, _FakeCompanyService]:
    service = InvoiceService.__new__(InvoiceService)
    fake_repo = _FakeInvoiceRepo()
    fake_repo.conflicting_rows = conflicting_rows or []
    fake_trip_catch_service = _FakeTripCatchService(trip_catch=trip_catch, raises=trip_catch_raises)
    fake_company_service = _FakeCompanyService()
    fake_company_service.names_by_id = names_by_id or {}
    service._repo = fake_repo  # type: ignore[assignment]
    service._trip_catch_service = fake_trip_catch_service  # type: ignore[assignment]
    service._company_service = fake_company_service  # type: ignore[assignment]
    return service, fake_repo, fake_trip_catch_service, fake_company_service


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


class TestGetTripCatchDraftDemand:
    """InvoiceService.get_trip_catch_draft_demand - Sprint 15 Session 5. The
    aggregation logic itself is integration-tested (TestSumOtherDraftQuantity
    in test_invoice_repository.py); this class covers what the service adds
    on top: trip-catch existence/tenant validation, error translation, and
    correct forwarding of exclude_invoice_id."""

    async def test_returns_the_repository_sum_as_is(self) -> None:
        trip_catch = _TripCatchStub()
        service, fake_repo, _ = _service_with_draft_demand_fakes(
            trip_catch=trip_catch, other_draft_quantity=Decimal("40.000")
        )

        result = await service.get_trip_catch_draft_demand(
            trip_catch.id, tenant_id=uuid.uuid4(), exclude_invoice_id=None
        )

        assert isinstance(result, TripCatchDraftDemandResponse)
        assert result.trip_catch_id == trip_catch.id
        assert result.other_draft_quantity == Decimal("40.000")

    async def test_raises_trip_catch_not_found_when_trip_catch_missing(self) -> None:
        service, _, _ = _service_with_draft_demand_fakes(trip_catch_raises=True)

        with pytest.raises(InvoiceItemTripCatchNotFoundError):
            await service.get_trip_catch_draft_demand(
                uuid.uuid4(), tenant_id=uuid.uuid4(), exclude_invoice_id=None
            )

    async def test_never_queries_the_aggregate_when_trip_catch_is_missing(self) -> None:
        """A 404 short-circuits before the (more expensive) aggregate query
        runs at all."""
        service, fake_repo, _ = _service_with_draft_demand_fakes(trip_catch_raises=True)

        with pytest.raises(InvoiceItemTripCatchNotFoundError):
            await service.get_trip_catch_draft_demand(
                uuid.uuid4(), tenant_id=uuid.uuid4(), exclude_invoice_id=None
            )

        assert fake_repo.sum_other_draft_quantity_calls == []

    async def test_forwards_tenant_id_and_exclude_invoice_id(self) -> None:
        trip_catch = _TripCatchStub()
        service, fake_repo, fake_trip_catch_service = _service_with_draft_demand_fakes(
            trip_catch=trip_catch
        )
        tenant_id = uuid.uuid4()
        exclude_invoice_id = uuid.uuid4()

        await service.get_trip_catch_draft_demand(
            trip_catch.id, tenant_id=tenant_id, exclude_invoice_id=exclude_invoice_id
        )

        assert fake_trip_catch_service.get_calls == [(trip_catch.id, tenant_id)]
        assert fake_repo.sum_other_draft_quantity_calls == [
            (trip_catch.id, tenant_id, exclude_invoice_id)
        ]

    async def test_exclude_invoice_id_is_optional(self) -> None:
        trip_catch = _TripCatchStub()
        service, fake_repo, _ = _service_with_draft_demand_fakes(trip_catch=trip_catch)
        tenant_id = uuid.uuid4()

        await service.get_trip_catch_draft_demand(
            trip_catch.id, tenant_id=tenant_id, exclude_invoice_id=None
        )

        assert fake_repo.sum_other_draft_quantity_calls == [(trip_catch.id, tenant_id, None)]

    async def test_zero_other_draft_quantity_is_returned_as_is(self) -> None:
        trip_catch = _TripCatchStub()
        service, _, _ = _service_with_draft_demand_fakes(
            trip_catch=trip_catch, other_draft_quantity=Decimal("0")
        )

        result = await service.get_trip_catch_draft_demand(
            trip_catch.id, tenant_id=uuid.uuid4(), exclude_invoice_id=None
        )

        assert result.other_draft_quantity == Decimal("0")


def _conflict_row(
    *,
    invoice_id: uuid.UUID | None = None,
    invoice_number: str | None = None,
    status: InvoiceStatus = InvoiceStatus.DRAFT,
    invoice_date: date = date(2026, 7, 22),
    company_id: uuid.UUID | None = None,
    quantity: Decimal = Decimal("10.000"),
) -> SimpleNamespace:
    """Stands in for one Row from InvoiceRepository.list_invoices_referencing_trip_catch -
    only attribute access is used by the service, never row-tuple unpacking."""
    return SimpleNamespace(
        id=invoice_id or uuid.uuid4(),
        invoice_number=invoice_number,
        status=status,
        invoice_date=invoice_date,
        company_id=company_id or uuid.uuid4(),
        quantity=quantity,
    )


class TestGetTripCatchConflicts:
    """InvoiceService.get_trip_catch_conflicts - Sprint 15 Session 6. The
    aggregation/filtering logic itself is integration-tested
    (TestListInvoicesReferencingTripCatch); this covers what the service
    adds: trip-catch validation, shortfall math, and bulk company-name
    resolution."""

    async def test_returns_conflicts_with_resolved_company_names(self) -> None:
        trip_catch = _TripCatchStub(available_quantity=Decimal("40.000"))
        company_id = uuid.uuid4()
        row = _conflict_row(company_id=company_id, quantity=Decimal("30.000"))
        service, _, _, fake_company_service = _service_with_conflict_fakes(
            trip_catch=trip_catch,
            conflicting_rows=[row],
            names_by_id={company_id: "ABC Traders"},
        )

        result = await service.get_trip_catch_conflicts(
            trip_catch.id, tenant_id=uuid.uuid4(), exclude_invoice_id=None, required_quantity=None
        )

        assert len(result.conflicting_invoices) == 1
        assert result.conflicting_invoices[0].company_name == "ABC Traders"
        assert result.conflicting_invoices[0].quantity == Decimal("30.000")
        assert fake_company_service.get_names_by_ids_calls  # resolved in bulk, not per-row

    async def test_unresolvable_company_name_falls_back_without_raising(self) -> None:
        trip_catch = _TripCatchStub()
        row = _conflict_row(quantity=Decimal("5.000"))
        service, _, _, _ = _service_with_conflict_fakes(
            trip_catch=trip_catch, conflicting_rows=[row], names_by_id={}
        )

        result = await service.get_trip_catch_conflicts(
            trip_catch.id, tenant_id=uuid.uuid4(), exclude_invoice_id=None, required_quantity=None
        )

        assert result.conflicting_invoices[0].company_name == "Unknown Company"

    async def test_computes_shortfall_when_required_quantity_given(self) -> None:
        trip_catch = _TripCatchStub(available_quantity=Decimal("40.000"))
        service, _, _, _ = _service_with_conflict_fakes(trip_catch=trip_catch)

        result = await service.get_trip_catch_conflicts(
            trip_catch.id,
            tenant_id=uuid.uuid4(),
            exclude_invoice_id=None,
            required_quantity=Decimal("50.000"),
        )

        assert result.available_quantity == Decimal("40.000")
        assert result.required_quantity == Decimal("50.000")
        assert result.shortfall_quantity == Decimal("10.000")

    async def test_shortfall_never_negative_when_enough_is_available(self) -> None:
        """required_quantity may legitimately be <= available (e.g. the UI
        re-checks after someone else's draft was deleted) - shortfall must
        floor at zero, never go negative."""
        trip_catch = _TripCatchStub(available_quantity=Decimal("100.000"))
        service, _, _, _ = _service_with_conflict_fakes(trip_catch=trip_catch)

        result = await service.get_trip_catch_conflicts(
            trip_catch.id,
            tenant_id=uuid.uuid4(),
            exclude_invoice_id=None,
            required_quantity=Decimal("40.000"),
        )

        assert result.shortfall_quantity == Decimal("0")

    async def test_shortfall_is_none_when_required_quantity_not_given(self) -> None:
        trip_catch = _TripCatchStub()
        service, _, _, _ = _service_with_conflict_fakes(trip_catch=trip_catch)

        result = await service.get_trip_catch_conflicts(
            trip_catch.id, tenant_id=uuid.uuid4(), exclude_invoice_id=None, required_quantity=None
        )

        assert result.required_quantity is None
        assert result.shortfall_quantity is None

    async def test_raises_trip_catch_not_found_when_trip_catch_missing(self) -> None:
        service, _, _, _ = _service_with_conflict_fakes(trip_catch_raises=True)

        with pytest.raises(InvoiceItemTripCatchNotFoundError):
            await service.get_trip_catch_conflicts(
                uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                exclude_invoice_id=None,
                required_quantity=None,
            )

    async def test_never_queries_conflicts_when_trip_catch_is_missing(self) -> None:
        service, fake_repo, _, fake_company_service = _service_with_conflict_fakes(
            trip_catch_raises=True
        )

        with pytest.raises(InvoiceItemTripCatchNotFoundError):
            await service.get_trip_catch_conflicts(
                uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                exclude_invoice_id=None,
                required_quantity=None,
            )

        assert fake_repo.list_conflicts_calls == []
        assert fake_company_service.get_names_by_ids_calls == []

    async def test_forwards_tenant_id_and_exclude_invoice_id(self) -> None:
        trip_catch = _TripCatchStub()
        service, fake_repo, fake_trip_catch_service, _ = _service_with_conflict_fakes(
            trip_catch=trip_catch
        )
        tenant_id = uuid.uuid4()
        exclude_invoice_id = uuid.uuid4()

        await service.get_trip_catch_conflicts(
            trip_catch.id,
            tenant_id=tenant_id,
            exclude_invoice_id=exclude_invoice_id,
            required_quantity=None,
        )

        assert fake_trip_catch_service.get_calls == [(trip_catch.id, tenant_id)]
        assert fake_repo.list_conflicts_calls == [(trip_catch.id, tenant_id, exclude_invoice_id)]

    async def test_no_conflicts_returns_empty_list(self) -> None:
        trip_catch = _TripCatchStub()
        service, _, _, _ = _service_with_conflict_fakes(trip_catch=trip_catch, conflicting_rows=[])

        result = await service.get_trip_catch_conflicts(
            trip_catch.id, tenant_id=uuid.uuid4(), exclude_invoice_id=None, required_quantity=None
        )

        assert result.conflicting_invoices == []

    async def test_multiple_conflicts_each_keep_their_own_company_name(self) -> None:
        trip_catch = _TripCatchStub()
        company_a, company_b = uuid.uuid4(), uuid.uuid4()
        rows = [
            _conflict_row(company_id=company_a, quantity=Decimal("20.000")),
            _conflict_row(company_id=company_b, quantity=Decimal("30.000")),
        ]
        service, _, _, _ = _service_with_conflict_fakes(
            trip_catch=trip_catch,
            conflicting_rows=rows,
            names_by_id={company_a: "Alpha Traders", company_b: "Beta Traders"},
        )

        result = await service.get_trip_catch_conflicts(
            trip_catch.id, tenant_id=uuid.uuid4(), exclude_invoice_id=None, required_quantity=None
        )

        names = {c.company_name for c in result.conflicting_invoices}
        assert names == {"Alpha Traders", "Beta Traders"}


def _usage_row(
    *,
    trip_catch_id: uuid.UUID | None = None,
    invoice_count: int = 1,
    draft_quantity: Decimal = Decimal("0"),
    consumed_quantity: Decimal = Decimal("0"),
) -> SimpleNamespace:
    """Stands in for one Row from InvoiceRepository.get_trip_catch_invoice_usage -
    only attribute access is used by the service, never row-tuple unpacking."""
    return SimpleNamespace(
        trip_catch_id=trip_catch_id or uuid.uuid4(),
        invoice_count=invoice_count,
        draft_quantity=draft_quantity,
        consumed_quantity=consumed_quantity,
    )


def _service_with_usage_fakes(
    *, usage_rows: list[Any] | None = None
) -> tuple[InvoiceService, _FakeInvoiceRepo]:
    service = InvoiceService.__new__(InvoiceService)
    fake_repo = _FakeInvoiceRepo()
    fake_repo.usage_rows = usage_rows or []
    service._repo = fake_repo  # type: ignore[assignment]
    return service, fake_repo


class TestGetTripCatchInvoiceUsage:
    """InvoiceService.get_trip_catch_invoice_usage - Sprint 15 Session 7.
    The aggregation/filtering logic itself is integration-tested
    (TestGetTripCatchInvoiceUsage in test_invoice_repository.py); this
    covers what the service adds: the empty-input short-circuit and
    row-to-response mapping."""

    async def test_empty_ids_returns_empty_list_without_querying(self) -> None:
        service, fake_repo = _service_with_usage_fakes()

        result = await service.get_trip_catch_invoice_usage([], tenant_id=uuid.uuid4())

        assert result == []
        assert fake_repo.usage_calls == []

    async def test_maps_row_to_response(self) -> None:
        trip_catch_id = uuid.uuid4()
        row = _usage_row(
            trip_catch_id=trip_catch_id,
            invoice_count=2,
            draft_quantity=Decimal("30.000"),
            consumed_quantity=Decimal("60.000"),
        )
        service, _ = _service_with_usage_fakes(usage_rows=[row])

        result = await service.get_trip_catch_invoice_usage([trip_catch_id], tenant_id=uuid.uuid4())

        assert len(result) == 1
        assert result[0].trip_catch_id == trip_catch_id
        assert result[0].invoice_count == 2
        assert result[0].draft_quantity == Decimal("30.000")
        assert result[0].consumed_quantity == Decimal("60.000")

    async def test_multiple_rows_mapped_independently(self) -> None:
        catch_a, catch_b = uuid.uuid4(), uuid.uuid4()
        rows = [
            _usage_row(trip_catch_id=catch_a, invoice_count=1, draft_quantity=Decimal("10.000")),
            _usage_row(trip_catch_id=catch_b, invoice_count=3, consumed_quantity=Decimal("40.000")),
        ]
        service, _ = _service_with_usage_fakes(usage_rows=rows)

        result = await service.get_trip_catch_invoice_usage(
            [catch_a, catch_b], tenant_id=uuid.uuid4()
        )

        by_id = {r.trip_catch_id: r for r in result}
        assert by_id[catch_a].invoice_count == 1
        assert by_id[catch_a].draft_quantity == Decimal("10.000")
        assert by_id[catch_b].invoice_count == 3
        assert by_id[catch_b].consumed_quantity == Decimal("40.000")

    async def test_a_trip_catch_absent_from_repo_result_is_absent_from_response(self) -> None:
        """A trip catch with no qualifying invoice never gets a synthesized
        zero-row - it's simply absent, matching the repository's own
        contract (missing means zero usage)."""
        requested = [uuid.uuid4(), uuid.uuid4()]
        row = _usage_row(trip_catch_id=requested[0], invoice_count=1)
        service, _ = _service_with_usage_fakes(usage_rows=[row])

        result = await service.get_trip_catch_invoice_usage(requested, tenant_id=uuid.uuid4())

        assert len(result) == 1
        assert result[0].trip_catch_id == requested[0]

    async def test_forwards_ids_and_tenant_to_repository(self) -> None:
        service, fake_repo = _service_with_usage_fakes()
        ids = [uuid.uuid4(), uuid.uuid4()]
        tenant_id = uuid.uuid4()

        await service.get_trip_catch_invoice_usage(ids, tenant_id=tenant_id)

        assert fake_repo.usage_calls == [(ids, tenant_id, None)]

    async def test_no_rows_returns_empty_list(self) -> None:
        service, _ = _service_with_usage_fakes(usage_rows=[])

        result = await service.get_trip_catch_invoice_usage([uuid.uuid4()], tenant_id=uuid.uuid4())

        assert result == []


def _conflicts_service_with_fakes(
    *,
    invoice: Invoice | None = None,
    items: list[InvoiceItem] | None = None,
    usage_rows: list[Any] | None = None,
) -> tuple[InvoiceService, _FakeInvoiceRepo]:
    service = InvoiceService.__new__(InvoiceService)
    fake_repo = _FakeInvoiceRepo()
    if invoice is not None:
        fake_repo.by_id[invoice.id] = invoice
        fake_repo.items_by_invoice[invoice.id] = items or []
    fake_repo.usage_rows = usage_rows or []
    service._repo = fake_repo  # type: ignore[assignment]
    return service, fake_repo


class TestGetInvoiceTripCatchConflicts:
    """InvoiceService.get_invoice_trip_catch_conflicts - Sprint 15 Session 8.
    The aggregation/filtering/exclusion logic itself is integration-tested
    (test_invoice_repository.py's TestGetTripCatchInvoiceUsage exclude_invoice_id
    coverage, and test_invoice_api.py's TestGetInvoiceTripCatchConflicts); this
    covers what the service adds on top: invoice existence/tenant scoping via
    _get_or_raise, collecting distinct trip_catch_ids from this invoice's own
    items (in order of first appearance), forwarding exclude_invoice_id=invoice_id,
    and zero-filling a trip catch absent from the repository's result."""

    async def test_raises_not_found_when_invoice_missing(self) -> None:
        service, _ = _conflicts_service_with_fakes()

        with pytest.raises(InvoiceNotFoundError):
            await service.get_invoice_trip_catch_conflicts(uuid.uuid4(), tenant_id=uuid.uuid4())

    async def test_returns_empty_list_when_invoice_has_no_items(self) -> None:
        invoice = _make_invoice()
        service, fake_repo = _conflicts_service_with_fakes(invoice=invoice, items=[])

        result = await service.get_invoice_trip_catch_conflicts(
            invoice.id, tenant_id=invoice.tenant_id
        )

        assert result == []
        assert fake_repo.usage_calls == []

    async def test_returns_empty_list_when_no_item_has_a_trip_catch_id(self) -> None:
        invoice = _make_invoice()
        item = _make_invoice_item(
            invoice_id=invoice.id, tenant_id=invoice.tenant_id, trip_catch_id=None
        )
        service, fake_repo = _conflicts_service_with_fakes(invoice=invoice, items=[item])

        result = await service.get_invoice_trip_catch_conflicts(
            invoice.id, tenant_id=invoice.tenant_id
        )

        assert result == []
        assert fake_repo.usage_calls == []

    async def test_forwards_the_current_invoice_id_as_exclude_invoice_id(self) -> None:
        invoice = _make_invoice()
        item = _make_invoice_item(invoice_id=invoice.id, tenant_id=invoice.tenant_id)
        service, fake_repo = _conflicts_service_with_fakes(invoice=invoice, items=[item])

        await service.get_invoice_trip_catch_conflicts(invoice.id, tenant_id=invoice.tenant_id)

        assert fake_repo.usage_calls == [([item.trip_catch_id], invoice.tenant_id, invoice.id)]

    async def test_deduplicates_trip_catch_ids_across_multiple_items(self) -> None:
        invoice = _make_invoice()
        shared_catch = uuid.uuid4()
        item_a = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=shared_catch,
            line_number=1,
        )
        item_b = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=shared_catch,
            line_number=2,
        )
        service, fake_repo = _conflicts_service_with_fakes(invoice=invoice, items=[item_a, item_b])

        await service.get_invoice_trip_catch_conflicts(invoice.id, tenant_id=invoice.tenant_id)

        assert fake_repo.usage_calls == [([shared_catch], invoice.tenant_id, invoice.id)]

    async def test_zero_fills_a_trip_catch_absent_from_the_usage_rows(self) -> None:
        invoice = _make_invoice()
        item = _make_invoice_item(invoice_id=invoice.id, tenant_id=invoice.tenant_id)
        service, _ = _conflicts_service_with_fakes(invoice=invoice, items=[item], usage_rows=[])

        result = await service.get_invoice_trip_catch_conflicts(
            invoice.id, tenant_id=invoice.tenant_id
        )

        assert len(result) == 1
        assert result[0].trip_catch_id == item.trip_catch_id
        assert result[0].other_invoice_count == 0
        assert result[0].other_draft_quantity == Decimal("0.000")
        assert result[0].other_consumed_quantity == Decimal("0.000")

    async def test_maps_usage_row_fields_onto_the_other_prefixed_response(self) -> None:
        invoice = _make_invoice()
        item = _make_invoice_item(invoice_id=invoice.id, tenant_id=invoice.tenant_id)
        row = _usage_row(
            trip_catch_id=item.trip_catch_id,
            invoice_count=2,
            draft_quantity=Decimal("20.000"),
            consumed_quantity=Decimal("40.000"),
        )
        service, _ = _conflicts_service_with_fakes(invoice=invoice, items=[item], usage_rows=[row])

        result = await service.get_invoice_trip_catch_conflicts(
            invoice.id, tenant_id=invoice.tenant_id
        )

        assert result[0].other_invoice_count == 2
        assert result[0].other_draft_quantity == Decimal("20.000")
        assert result[0].other_consumed_quantity == Decimal("40.000")

    async def test_multiple_trip_catches_remain_independent_and_ordered(self) -> None:
        invoice = _make_invoice()
        catch_a, catch_b = uuid.uuid4(), uuid.uuid4()
        item_a = _make_invoice_item(
            invoice_id=invoice.id, tenant_id=invoice.tenant_id, trip_catch_id=catch_a, line_number=1
        )
        item_b = _make_invoice_item(
            invoice_id=invoice.id, tenant_id=invoice.tenant_id, trip_catch_id=catch_b, line_number=2
        )
        row_a = _usage_row(
            trip_catch_id=catch_a, invoice_count=2, consumed_quantity=Decimal("15.000")
        )
        service, _ = _conflicts_service_with_fakes(
            invoice=invoice, items=[item_a, item_b], usage_rows=[row_a]
        )

        result = await service.get_invoice_trip_catch_conflicts(
            invoice.id, tenant_id=invoice.tenant_id
        )

        assert [r.trip_catch_id for r in result] == [catch_a, catch_b]
        assert result[0].other_invoice_count == 2
        assert result[1].other_invoice_count == 0
        assert result[1].other_draft_quantity == Decimal("0")


def _preflight_service_with_fakes(
    *,
    invoice: Invoice | None = None,
    items: list[InvoiceItem] | None = None,
    trip_catches: list[_TripCatchStub] | None = None,
    usage_rows: list[Any] | None = None,
) -> tuple[InvoiceService, _FakeInvoiceRepo, _FakeTripCatchService]:
    service = InvoiceService.__new__(InvoiceService)
    fake_repo = _FakeInvoiceRepo()
    if invoice is not None:
        fake_repo.by_id[invoice.id] = invoice
        fake_repo.items_by_invoice[invoice.id] = items or []
    fake_repo.usage_rows = usage_rows or []
    fake_trip_catch_service = _FakeTripCatchService()
    fake_trip_catch_service.many_by_id = {tc.id: tc for tc in (trip_catches or [])}
    service._repo = fake_repo  # type: ignore[assignment]
    service._trip_catch_service = fake_trip_catch_service  # type: ignore[assignment]
    return service, fake_repo, fake_trip_catch_service


class TestGetIssuePreflight:
    """InvoiceService.get_issue_preflight - Sprint 15 Session 10. The
    aggregation/filtering logic itself is integration-tested
    (test_invoice_api.py's TestGetInvoiceIssuePreflight); this covers what
    the service adds: invoice existence/tenant/draft-only gating, collecting
    and summing this invoice's own requested quantity per distinct trip
    catch, comparing against live available_quantity, and only surfacing
    genuinely insufficient catches."""

    async def test_raises_not_found_when_invoice_missing(self) -> None:
        service, _, _ = _preflight_service_with_fakes()

        with pytest.raises(InvoiceNotFoundError):
            await service.get_issue_preflight(uuid.uuid4(), tenant_id=uuid.uuid4())

    async def test_raises_not_draft_for_an_already_issued_invoice(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.ISSUED)
        service, _, _ = _preflight_service_with_fakes(invoice=invoice, items=[])

        with pytest.raises(InvoiceNotDraftError):
            await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

    async def test_clean_preflight_when_invoice_has_no_items(self) -> None:
        invoice = _make_invoice()
        service, fake_repo, fake_trip_catch_service = _preflight_service_with_fakes(
            invoice=invoice, items=[]
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert result.can_issue_now is True
        assert result.conflicts == []
        assert fake_trip_catch_service.get_many_by_ids_calls == []
        assert fake_repo.usage_calls == []

    async def test_clean_preflight_when_available_quantity_is_sufficient(self) -> None:
        invoice = _make_invoice()
        catch = _TripCatchStub(available_quantity=Decimal("100.000"))
        item = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=catch.id,
            quantity=Decimal("30.000"),
        )
        service, _, _ = _preflight_service_with_fakes(
            invoice=invoice, items=[item], trip_catches=[catch]
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert result.can_issue_now is True
        assert result.conflicts == []

    async def test_flags_a_trip_catch_with_insufficient_available_quantity(self) -> None:
        invoice = _make_invoice()
        catch = _TripCatchStub(available_quantity=Decimal("25.000"))
        item = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=catch.id,
            quantity=Decimal("30.000"),
        )
        service, _, _ = _preflight_service_with_fakes(
            invoice=invoice, items=[item], trip_catches=[catch]
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert result.can_issue_now is False
        assert len(result.conflicts) == 1
        conflict = result.conflicts[0]
        assert conflict.trip_catch_id == catch.id
        assert conflict.requested_quantity == Decimal("30.000")
        assert conflict.available_quantity == Decimal("25.000")
        assert conflict.is_sufficient is False
        assert conflict.shortfall_quantity == Decimal("5.000")

    async def test_requested_quantity_exactly_equal_to_available_is_sufficient(self) -> None:
        invoice = _make_invoice()
        catch = _TripCatchStub(available_quantity=Decimal("30.000"))
        item = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=catch.id,
            quantity=Decimal("30.000"),
        )
        service, _, _ = _preflight_service_with_fakes(
            invoice=invoice, items=[item], trip_catches=[catch]
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert result.can_issue_now is True
        assert result.conflicts == []

    async def test_sums_multiple_items_on_the_same_trip_catch(self) -> None:
        invoice = _make_invoice()
        catch = _TripCatchStub(available_quantity=Decimal("30.000"))
        item_a = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=catch.id,
            line_number=1,
            quantity=Decimal("20.000"),
        )
        item_b = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=catch.id,
            line_number=2,
            quantity=Decimal("15.000"),
        )
        service, _, _ = _preflight_service_with_fakes(
            invoice=invoice, items=[item_a, item_b], trip_catches=[catch]
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert len(result.conflicts) == 1
        # 20 + 15 = 35 requested vs. 30 available - one conflict, not two.
        assert result.conflicts[0].requested_quantity == Decimal("35.000")
        assert result.conflicts[0].shortfall_quantity == Decimal("5.000")

    async def test_multiple_trip_catches_remain_independent(self) -> None:
        invoice = _make_invoice()
        sufficient_catch = _TripCatchStub(available_quantity=Decimal("100.000"))
        insufficient_catch = _TripCatchStub(available_quantity=Decimal("10.000"))
        item_a = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=sufficient_catch.id,
            line_number=1,
            quantity=Decimal("20.000"),
        )
        item_b = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=insufficient_catch.id,
            line_number=2,
            quantity=Decimal("20.000"),
        )
        service, _, _ = _preflight_service_with_fakes(
            invoice=invoice,
            items=[item_a, item_b],
            trip_catches=[sufficient_catch, insufficient_catch],
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert result.can_issue_now is False
        assert len(result.conflicts) == 1
        assert result.conflicts[0].trip_catch_id == insufficient_catch.id

    async def test_missing_trip_catch_is_treated_as_zero_available(self) -> None:
        """A trip catch absent from get_many_by_ids's result (soft-deleted
        since the item was added, or belongs to another tenant) is treated
        as zero available - a conflict, even though the real issue() would
        raise a different, more specific not-found error in that exact
        case."""
        invoice = _make_invoice()
        missing_catch_id = uuid.uuid4()
        item = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=missing_catch_id,
            quantity=Decimal("10.000"),
        )
        service, _, _ = _preflight_service_with_fakes(
            invoice=invoice, items=[item], trip_catches=[]
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert result.can_issue_now is False
        assert result.conflicts[0].available_quantity == Decimal("0")

    async def test_includes_other_draft_quantity_from_the_shared_usage_aggregate(self) -> None:
        invoice = _make_invoice()
        catch = _TripCatchStub(available_quantity=Decimal("10.000"))
        item = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=catch.id,
            quantity=Decimal("30.000"),
        )
        row = _usage_row(trip_catch_id=catch.id, invoice_count=1, draft_quantity=Decimal("15.000"))
        service, _, _ = _preflight_service_with_fakes(
            invoice=invoice, items=[item], trip_catches=[catch], usage_rows=[row]
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert result.conflicts[0].other_draft_quantity == Decimal("15.000")

    async def test_forwards_exclude_invoice_id_to_the_usage_aggregate(self) -> None:
        invoice = _make_invoice()
        catch = _TripCatchStub(available_quantity=Decimal("5.000"))
        item = _make_invoice_item(
            invoice_id=invoice.id,
            tenant_id=invoice.tenant_id,
            trip_catch_id=catch.id,
            quantity=Decimal("10.000"),
        )
        service, fake_repo, fake_trip_catch_service = _preflight_service_with_fakes(
            invoice=invoice, items=[item], trip_catches=[catch]
        )

        await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert fake_repo.usage_calls == [([catch.id], invoice.tenant_id, invoice.id)]
        assert fake_trip_catch_service.get_many_by_ids_calls == [([catch.id], invoice.tenant_id)]

    async def test_items_with_no_trip_catch_id_are_skipped(self) -> None:
        invoice = _make_invoice()
        item = _make_invoice_item(
            invoice_id=invoice.id, tenant_id=invoice.tenant_id, trip_catch_id=None
        )
        service, _, fake_trip_catch_service = _preflight_service_with_fakes(
            invoice=invoice, items=[item]
        )

        result = await service.get_issue_preflight(invoice.id, tenant_id=invoice.tenant_id)

        assert result.can_issue_now is True
        assert result.conflicts == []
        assert fake_trip_catch_service.get_many_by_ids_calls == []


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

    async def test_forwards_trip_catch_error_details_unchanged(self) -> None:
        """Sprint 15 Session 6: InvoiceInsufficientInventoryError must carry
        the same `details` TripCatchInsufficientQuantityError raised with -
        the conflict-resolution UI reads trip_catch_id from here."""
        invoice = _make_invoice(status=InvoiceStatus.DRAFT)
        item = _make_invoice_item(invoice_id=invoice.id, tenant_id=invoice.tenant_id)
        company = _CompanyStub(company_id=invoice.company_id, status=CompanyStatus.ACTIVE)
        details = {
            "trip_catch_id": str(item.trip_catch_id),
            "requested_quantity": "50.000",
            "available_quantity": "40.000",
        }
        service, _, _, _, _ = _issue_service_with_fakes(
            invoice=invoice,
            items=[item],
            company=company,
            trip_catch_raises=TripCatchInsufficientQuantityError("not enough", details=details),
        )

        with pytest.raises(InvoiceInsufficientInventoryError) as exc_info:
            await service.issue(invoice.id, tenant_id=invoice.tenant_id, actor_id=uuid.uuid4())

        assert exc_info.value.details == details

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


class _FakeFlushSession:
    """Stands in for AsyncSession - recalculate_payment_totals only ever
    calls .flush() on it (the happy-path commit/refresh belongs to the
    caller, PaymentService, and is integration-tested instead)."""

    def __init__(self) -> None:
        self.flush_calls = 0

    async def flush(self) -> None:
        self.flush_calls += 1


def _reconciliation_service_with_fakes(
    *, invoice: Invoice | None, open_balance_by_company: Decimal = Decimal("0")
) -> tuple[InvoiceService, _FakeInvoiceRepo, _FakeCompanyService, _FakeFlushSession]:
    service = InvoiceService.__new__(InvoiceService)
    fake_repo = _FakeInvoiceRepo()
    if invoice is not None:
        fake_repo.by_id[invoice.id] = invoice
        fake_repo.open_balance_by_company[invoice.company_id] = open_balance_by_company
    fake_company_service = _FakeCompanyService()
    fake_session = _FakeFlushSession()
    service._repo = fake_repo  # type: ignore[assignment]
    service._company_service = fake_company_service  # type: ignore[assignment]
    service._session = fake_session  # type: ignore[assignment]
    return service, fake_repo, fake_company_service, fake_session


class TestRecalculatePaymentTotals:
    """InvoiceService.recalculate_payment_totals - Sprint 10 Session 4's
    outstanding engine. PaymentService is the only caller; it computes
    total_allocated via its own PaymentRepository and passes it in."""

    async def test_zero_allocated_leaves_the_invoice_issued(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.ISSUED, total_amount=Decimal("1000.00"))
        service, _, _, _ = _reconciliation_service_with_fakes(invoice=invoice)

        await service.recalculate_payment_totals(
            invoice.id, tenant_id=invoice.tenant_id, total_allocated=Decimal("0")
        )

        assert invoice.paid_amount == Decimal("0.00")
        assert invoice.balance_amount == Decimal("1000.00")
        assert invoice.status == InvoiceStatus.ISSUED

    async def test_partial_allocation_moves_the_invoice_to_partially_paid(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.ISSUED, total_amount=Decimal("1000.00"))
        service, _, _, _ = _reconciliation_service_with_fakes(invoice=invoice)

        await service.recalculate_payment_totals(
            invoice.id, tenant_id=invoice.tenant_id, total_allocated=Decimal("400.00")
        )

        assert invoice.paid_amount == Decimal("400.00")
        assert invoice.balance_amount == Decimal("600.00")
        assert invoice.status == InvoiceStatus.PARTIALLY_PAID

    async def test_full_allocation_moves_the_invoice_to_paid(self) -> None:
        invoice = _make_invoice(
            status=InvoiceStatus.PARTIALLY_PAID, total_amount=Decimal("1000.00")
        )
        service, _, _, _ = _reconciliation_service_with_fakes(invoice=invoice)

        await service.recalculate_payment_totals(
            invoice.id, tenant_id=invoice.tenant_id, total_allocated=Decimal("1000.00")
        )

        assert invoice.status == InvoiceStatus.PAID

    async def test_removing_allocations_moves_a_paid_invoice_back_down(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.PAID, total_amount=Decimal("1000.00"))
        service, _, _, _ = _reconciliation_service_with_fakes(invoice=invoice)

        await service.recalculate_payment_totals(
            invoice.id, tenant_id=invoice.tenant_id, total_allocated=Decimal("250.00")
        )

        assert invoice.status == InvoiceStatus.PARTIALLY_PAID
        assert invoice.balance_amount == Decimal("750.00")

    async def test_draft_invoice_raises_reconciliation_error(self) -> None:
        """Not reachable through the API - an allocation can only ever be
        created against an ISSUED/PARTIALLY_PAID invoice - but this module
        must not silently recalculate one outside the payment lifecycle."""
        invoice = _make_invoice(status=InvoiceStatus.DRAFT, total_amount=Decimal("1000.00"))
        service, _, _, _ = _reconciliation_service_with_fakes(invoice=invoice)

        with pytest.raises(InvoiceReconciliationError):
            await service.recalculate_payment_totals(
                invoice.id, tenant_id=invoice.tenant_id, total_allocated=Decimal("0")
            )

    async def test_raises_not_found_when_invoice_missing(self) -> None:
        service, _, _, _ = _reconciliation_service_with_fakes(invoice=None)

        with pytest.raises(InvoiceNotFoundError):
            await service.recalculate_payment_totals(
                uuid.uuid4(), tenant_id=uuid.uuid4(), total_allocated=Decimal("0")
            )

    async def test_flushes_before_summing_the_companys_open_balance(self) -> None:
        """recalculate_payment_totals must flush its own invoice.balance_amount
        write before reading sum_open_balance_by_company - this session's
        autoflush is disabled (app.db.session), so without an explicit flush
        that SUM would read a stale balance_amount for this very invoice."""
        invoice = _make_invoice(status=InvoiceStatus.ISSUED, total_amount=Decimal("1000.00"))
        service, fake_repo, _, fake_session = _reconciliation_service_with_fakes(invoice=invoice)

        await service.recalculate_payment_totals(
            invoice.id, tenant_id=invoice.tenant_id, total_allocated=Decimal("400.00")
        )

        assert fake_session.flush_calls == 1
        assert fake_repo.sum_open_balance_calls == [(invoice.company_id, invoice.tenant_id)]

    async def test_cascades_into_company_outstanding_recalculation(self) -> None:
        invoice = _make_invoice(status=InvoiceStatus.ISSUED, total_amount=Decimal("1000.00"))
        service, _, fake_company_service, _ = _reconciliation_service_with_fakes(
            invoice=invoice, open_balance_by_company=Decimal("2500.00")
        )

        await service.recalculate_payment_totals(
            invoice.id, tenant_id=invoice.tenant_id, total_allocated=Decimal("400.00")
        )

        assert fake_company_service.recalculate_outstanding_calls == [
            (invoice.company_id, invoice.tenant_id, Decimal("2500.00"))
        ]


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
