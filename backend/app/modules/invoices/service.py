import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.companies.constants import CompanyStatus
from app.modules.companies.exceptions import CompanyNotFoundError
from app.modules.companies.schemas import CompanyResponse
from app.modules.companies.service import CompanyService
from app.modules.fish.exceptions import FishNotFoundError
from app.modules.fish.service import FishService
from app.modules.invoices.constants import INVOICE_NUMBER_PREFIX, InvoiceStatus
from app.modules.invoices.domain.numbering import fiscal_year_for, format_invoice_number
from app.modules.invoices.domain.totals import (
    FinancialCalculationError,
    LineTotals,
    calculate_invoice_totals,
    calculate_line_totals,
)
from app.modules.invoices.exceptions import (
    InvoiceCalculationError,
    InvoiceCompanyInactiveError,
    InvoiceCompanyNotFoundError,
    InvoiceEmptyError,
    InvoiceInsufficientInventoryError,
    InvoiceItemFishMismatchError,
    InvoiceItemFishNotFoundError,
    InvoiceItemNotFoundError,
    InvoiceItemQuantityExceedsAvailableError,
    InvoiceItemTripCatchNotFoundError,
    InvoiceNotDraftError,
    InvoiceNotFoundError,
    InvoiceNumberConflictError,
)
from app.modules.invoices.models import Invoice, InvoiceItem
from app.modules.invoices.repository import InvoiceRepository
from app.modules.invoices.schemas import (
    InvoiceCreateRequest,
    InvoiceItemCreateRequest,
    InvoiceItemResponse,
    InvoiceItemUpdateRequest,
    InvoiceListParams,
    InvoiceResponse,
    InvoiceUpdateRequest,
)
from app.modules.trip_catches.exceptions import (
    TripCatchInsufficientQuantityError,
    TripCatchNotFoundError,
)
from app.modules.trip_catches.schemas import TripCatchResponse
from app.modules.trip_catches.service import TripCatchService


class InvoiceService:
    """Sprint 9 - draft invoice CRUD (Session 2), invoice item CRUD
    (Session 3), server-side financial calculation (Session 4), and the
    issue workflow (Session 5, see issue()). Every mutation that could
    change an invoice's totals (item added/updated/deleted, or the
    invoice's own transport_charge/other_charge changed) is followed by a
    full recalculation via _recalculate_invoice, which delegates the actual
    math to app.modules.invoices.domain.totals - never inline here.

    issue() is the one genuine business transaction in this module (as
    opposed to CRUD): draft -> issued is irreversible, assigns the
    invoice_number (app.modules.invoices.domain.numbering), deducts trip
    catch inventory (via TripCatchService, never its repository directly -
    ARCHITECTURE.md §2), and increases the billed company's
    outstanding_amount (via CompanyService), all inside one transaction.
    Every other method in this class enforces DRAFT-only mutation
    (_ensure_draft) as the immutability half of that same rule.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = InvoiceRepository(session)
        # Cross-module reference validation goes through the other module's
        # service, never its repository (ARCHITECTURE.md §2 - modules talk
        # to each other only through service.py).
        self._company_service = CompanyService(session)
        self._trip_catch_service = TripCatchService(session)
        self._fish_service = FishService(session)

    async def create(
        self, payload: InvoiceCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> InvoiceResponse:
        await self._ensure_company_active(payload.company_id, tenant_id)

        # invoice_number/status are fixed to NULL/DRAFT - neither is
        # client-supplied (see InvoiceCreateRequest); numbers are assigned
        # only at Session 5's issue. Every *calculated* financial column
        # starts at zero here and is immediately overwritten by
        # _recalculate_invoice below, which is what actually folds
        # transport_charge/other_charge into total_amount/balance_amount -
        # a brand-new invoice has no items yet, but still needs that.
        invoice = Invoice(
            tenant_id=tenant_id,
            company_id=payload.company_id,
            invoice_number=None,
            invoice_date=payload.invoice_date,
            due_date=payload.due_date,
            status=InvoiceStatus.DRAFT,
            subtotal=Decimal("0"),
            discount_amount=Decimal("0"),
            taxable_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            transport_charge=payload.transport_charge,
            other_charge=payload.other_charge,
            round_off=Decimal("0"),
            total_amount=Decimal("0"),
            paid_amount=Decimal("0"),
            balance_amount=Decimal("0"),
            remarks=payload.remarks,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(invoice)
        await self._session.flush()
        await self._recalculate_invoice(invoice, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(invoice)
        return self._to_response(invoice)

    async def get(self, invoice_id: uuid.UUID, *, tenant_id: uuid.UUID) -> InvoiceResponse:
        invoice = await self._get_or_raise(invoice_id, tenant_id)
        return self._to_response(invoice)

    async def list_invoices(
        self, *, tenant_id: uuid.UUID, params: InvoiceListParams
    ) -> PaginatedResponse[InvoiceResponse]:
        # Company-name search is resolved through CompanyService (not a
        # repository join) - modules never import another module's ORM
        # model directly.
        q_company_ids: list[uuid.UUID] | None = None
        if params.q and params.q.strip():
            q_company_ids = await self._company_service.find_ids_by_name(tenant_id, params.q)

        invoices, total = await self._repo.search(
            tenant_id,
            q=params.q,
            q_company_ids=q_company_ids,
            status=params.status,
            company_id=params.company_id,
            invoice_date_from=params.invoice_date_from,
            invoice_date_to=params.invoice_date_to,
            sort=params.sort,
            page=params.page,
            page_size=params.page_size,
        )
        total_pages = math.ceil(total / params.page_size) if total else 0
        meta = PaginationMeta(
            total_records=total,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.page_size,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )
        return PaginatedResponse(
            data=[self._to_response(invoice) for invoice in invoices], meta=meta
        )

    async def update(
        self,
        invoice_id: uuid.UUID,
        payload: InvoiceUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> InvoiceResponse:
        invoice = await self._get_or_raise(invoice_id, tenant_id)
        self._ensure_draft(invoice)
        update_data = payload.model_dump(exclude_unset=True)

        new_company_id = update_data.get("company_id", invoice.company_id)
        if "company_id" in update_data and new_company_id != invoice.company_id:
            await self._ensure_company_active(new_company_id, tenant_id)

        for field, value in update_data.items():
            setattr(invoice, field, value)
        invoice.updated_by = actor_id
        # Recalculated unconditionally, not only when transport_charge/
        # other_charge are present in the payload - trivial cost given a
        # small item count, and it rules out an entire class of "forgot to
        # recalculate for this field combination" bugs.
        await self._session.flush()
        await self._recalculate_invoice(invoice, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(invoice)
        return self._to_response(invoice)

    async def delete(
        self, invoice_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        invoice = await self._get_or_raise(invoice_id, tenant_id)
        self._ensure_draft(invoice)
        invoice.deleted_at = datetime.now(UTC)
        invoice.deleted_by = actor_id
        await self._session.commit()

    async def add_item(
        self,
        invoice_id: uuid.UUID,
        payload: InvoiceItemCreateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> InvoiceItemResponse:
        invoice = await self._get_or_raise(invoice_id, tenant_id)
        self._ensure_draft(invoice)
        await self._ensure_trip_catch_and_fish_valid(
            payload.trip_catch_id, payload.fish_id, payload.quantity, tenant_id=tenant_id
        )
        line_number = await self._repo.next_line_number(invoice_id, tenant_id)

        # Financial columns start at zero - none of them are client-
        # supplied (see InvoiceItemCreateRequest) - and are immediately
        # overwritten by _recalculate_invoice below, which computes this
        # item's real discount_amount/taxable_amount/tax_amount/line_total
        # (app.modules.invoices.domain.totals) along with the invoice's
        # aggregate totals.
        item = InvoiceItem(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            line_number=line_number,
            fish_id=payload.fish_id,
            trip_catch_id=payload.trip_catch_id,
            description=payload.description,
            quantity=payload.quantity,
            unit=payload.unit,
            rate=payload.rate,
            discount_percent=payload.discount_percent,
            discount_amount=Decimal("0"),
            taxable_amount=Decimal("0"),
            tax_rate=payload.tax_rate,
            tax_amount=Decimal("0"),
            line_total=Decimal("0"),
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add_item(item)
        await self._session.flush()
        await self._recalculate_invoice(invoice, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(item)
        return self._to_item_response(item)

    async def list_items(
        self, invoice_id: uuid.UUID, *, tenant_id: uuid.UUID, q: str | None
    ) -> list[InvoiceItemResponse]:
        # Listing is allowed regardless of invoice status - only add/edit/
        # delete are restricted to DRAFT.
        await self._get_or_raise(invoice_id, tenant_id)

        # Fish-name search is resolved through FishService (not a repository
        # join) - modules never import another module's ORM model directly.
        q_fish_ids: list[uuid.UUID] | None = None
        if q and q.strip():
            q_fish_ids = await self._fish_service.find_ids_by_name(tenant_id, q)

        items = await self._repo.search_items(invoice_id, tenant_id, q=q, q_fish_ids=q_fish_ids)
        return [self._to_item_response(item) for item in items]

    async def update_item(
        self,
        invoice_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: InvoiceItemUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> InvoiceItemResponse:
        invoice = await self._get_or_raise(invoice_id, tenant_id)
        self._ensure_draft(invoice)
        item = await self._get_item_or_raise(invoice_id, item_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)

        # Revalidate the full merged state on every update, regardless of
        # which fields actually changed - trip_catch.available_quantity (or
        # even the trip catch/fish rows themselves) may have moved since
        # this item was created.
        new_trip_catch_id = update_data.get("trip_catch_id", item.trip_catch_id)
        new_fish_id = update_data.get("fish_id", item.fish_id)
        new_quantity = update_data.get("quantity", item.quantity)
        if new_trip_catch_id is None:
            # Can't happen in practice - trip_catch_id is required at
            # creation (InvoiceItemCreateRequest) - but the column is
            # nullable at the DB level, so this satisfies both mypy's
            # narrowing and the "trip catch must exist" business rule if
            # that invariant were ever violated.
            raise InvoiceItemTripCatchNotFoundError("The specified trip catch does not exist")
        await self._ensure_trip_catch_and_fish_valid(
            new_trip_catch_id, new_fish_id, new_quantity, tenant_id=tenant_id
        )

        for field, value in update_data.items():
            setattr(item, field, value)
        item.updated_by = actor_id
        await self._session.flush()
        await self._recalculate_invoice(invoice, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(item)
        return self._to_item_response(item)

    async def delete_item(
        self,
        invoice_id: uuid.UUID,
        item_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        invoice = await self._get_or_raise(invoice_id, tenant_id)
        self._ensure_draft(invoice)
        item = await self._get_item_or_raise(invoice_id, item_id, tenant_id)
        item.deleted_at = datetime.now(UTC)
        item.deleted_by = actor_id
        await self._session.flush()
        await self._recalculate_invoice(invoice, tenant_id)
        await self._commit_or_raise()

    async def issue(
        self, invoice_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> InvoiceResponse:
        """The core business transaction of this module (TASKS.md Session 5)
        - draft -> issued, immutable from this point on. Everything below
        runs inside one transaction, committed only at the very end; any
        failure at any step rolls back all of it together (the invoice, its
        items' recalculated totals, every locked trip catch, and the
        company's outstanding_amount).

        Order of operations (ARCHITECTURE.md §13.3):
        1. Lock the invoice row (`SELECT ... FOR UPDATE`) - this alone is
           what makes a concurrent double-issue impossible, not just the
           DRAFT check below (two requests both reading status == draft
           before either writes would otherwise both proceed).
        2/3. get_by_id_for_update already scopes by tenant_id, so "does not
           exist" and "belongs to another tenant" are the same 404.
        4. Must be DRAFT - this single check also covers "cannot issue
           twice" (status is already ISSUED) and "cannot issue a cancelled
           invoice" (status is CANCELLED), the same guard every other
           mutating method here uses for immutability.
        5. Must have at least one active (non-deleted) item.
        Company must still exist and be active - checked at draft creation
           too, but it could have been deactivated since.
        6. Recalculate every total from scratch immediately before issuing
           (never trust whatever was last persisted), via the same
           _recalculate_invoice/domain.totals engine every other mutation
           uses.
        7/8/10. Lock and deduct every referenced trip catch's inventory, in
           a deterministic order (by trip_catch_id, not item order) - the
           same deadlock-avoidance rationale ARCHITECTURE.md §14.2 gives for
           locking invoices by id during payment allocation, applied here to
           two invoices concurrently issuing against overlapping trip
           catches. Revalidated under lock (TripCatchService.
           deduct_available_quantity), not against the possibly-stale value
           read when the item was originally added or last edited.
        9. Generate the invoice number only after inventory succeeds - not
           required for correctness (the whole transaction rolls back
           together regardless of ordering, so a failed issue never leaves
           a gap in the sequence either way), but avoids burning a number on
           an attempt that was always going to fail.
        11. Increase the company's outstanding_amount by total_amount.
        12/13. Mark ISSUED, stamp issued_at.
        14. Commit.

        Any failure at any step - including one raised after an earlier
        step's `flush()` has already sent writes to the database within
        this transaction - triggers an explicit rollback before the
        exception propagates. A closed, never-reused request-scoped session
        would eventually discard those unflushed writes on its own
        (app.db.session's get_db), but that's an incidental property of
        this app's session lifecycle, not a guarantee this method should
        lean on - "rollback everything if any step fails" (TASKS.md) is
        made explicit here rather than assumed.

        Extension points intentionally left unimplemented (TASKS.md: "no
        implementation yet"):
          - Ledger: INSERT ledger_entries (debit = total_amount).
          - PDF: generate_invoice_pdf, queued for a Celery worker.
          - Outbox/events: INSERT outbox_events(InvoiceIssued) for the
            dispatcher to notify/index/generate the PDF from.
          - Payment allocation (Sprint 10) will read balance_amount, which
            this method already leaves correct.
        """
        try:
            invoice = await self._repo.get_by_id_for_update(invoice_id, tenant_id)
            if invoice is None:
                raise InvoiceNotFoundError("Invoice not found")
            self._ensure_draft(invoice)

            items = await self._repo.search_items(invoice.id, tenant_id, q=None, q_fish_ids=None)
            if not items:
                raise InvoiceEmptyError("An invoice must have at least one item to be issued")

            await self._ensure_company_active(invoice.company_id, tenant_id)
            await self._recalculate_invoice(invoice, tenant_id)

            for item in sorted(items, key=lambda i: str(i.trip_catch_id)):
                if item.trip_catch_id is None:
                    # Can't happen in practice - trip_catch_id is required at
                    # item creation (InvoiceItemCreateRequest) - but the
                    # column is nullable at the DB level (ARCHITECTURE.md
                    # §16.1, a future untracked-stock line type), so this
                    # satisfies both mypy's narrowing and the "trip catch
                    # must exist" rule if that invariant were ever violated.
                    raise InvoiceItemTripCatchNotFoundError(
                        "The specified trip catch does not exist"
                    )
                try:
                    await self._trip_catch_service.deduct_available_quantity(
                        item.trip_catch_id, item.quantity, tenant_id=tenant_id, actor_id=actor_id
                    )
                except TripCatchNotFoundError as exc:
                    raise InvoiceItemTripCatchNotFoundError(
                        "The specified trip catch does not exist"
                    ) from exc
                except TripCatchInsufficientQuantityError as exc:
                    raise InvoiceInsufficientInventoryError(str(exc)) from exc
                # Flush after each deduction so the next iteration's FOR
                # UPDATE lookup (in the rare case two items share a
                # trip_catch_id) sees this one's change - this app's session
                # factory sets autoflush=False (app.db.session).
                await self._session.flush()

            invoice.invoice_number = await self._allocate_invoice_number(invoice, tenant_id)
            invoice.status = InvoiceStatus.ISSUED
            invoice.issued_at = datetime.now(UTC)
            invoice.updated_by = actor_id

            await self._company_service.increase_outstanding(
                invoice.company_id, invoice.total_amount, tenant_id=tenant_id
            )
        except Exception:
            await self._session.rollback()
            raise

        await self._commit_or_raise()
        await self._session.refresh(invoice)
        return self._to_response(invoice)

    async def _allocate_invoice_number(self, invoice: Invoice, tenant_id: uuid.UUID) -> str:
        """Concurrency-safe sequential number allocation (ARCHITECTURE.md
        §13.1): `INSERT ... ON CONFLICT DO NOTHING` guarantees the per-
        tenant/prefix/fiscal-year counter row exists without racing a
        concurrent first allocation for that fiscal year, then `SELECT ...
        FOR UPDATE` locks it so the increment below can never be lost to a
        concurrent issue. Only called from issue(), already inside its
        transaction - the row lock is held until that transaction commits
        or rolls back, serializing concurrent issues within one tenant/
        prefix/fiscal-year (ARCHITECTURE.md §13.1's documented contention
        trade-off)."""
        fiscal_year = fiscal_year_for(invoice.invoice_date)
        await self._repo.ensure_sequence_row(tenant_id, INVOICE_NUMBER_PREFIX, fiscal_year)
        sequence = await self._repo.get_sequence_for_update(
            tenant_id, INVOICE_NUMBER_PREFIX, fiscal_year
        )
        sequence.last_number += 1
        return format_invoice_number(INVOICE_NUMBER_PREFIX, fiscal_year, sequence.last_number)

    async def _recalculate_invoice(self, invoice: Invoice, tenant_id: uuid.UUID) -> None:
        """Recomputes every non-deleted item's discount_amount/
        taxable_amount/tax_amount/line_total and every invoice-level
        financial total from scratch, via app.modules.invoices.domain.totals
        - never inline here (TASKS.md Session 4: "Move calculation logic
        into totals.py, not service.py"). Called after every mutation that
        could change them: item added/updated/deleted, or the invoice's own
        transport_charge/other_charge changed.

        Recomputing every item unconditionally - not only the one that
        changed - is deliberate: each item's line totals are a pure
        function of its own quantity/rate/discount_percent/tax_rate, so
        this can never drift into a stale value, and an invoice's item
        count is small enough that the extra writes are negligible.

        Callers must `await self._session.flush()` first - this app's
        session factory sets `autoflush=False` (app.db.session), so without
        an explicit flush this method's read of the item list would miss
        whatever the caller just added/changed/soft-deleted.
        """
        items = await self._repo.search_items(invoice.id, tenant_id, q=None, q_fish_ids=None)

        try:
            line_totals: list[LineTotals] = []
            for item in items:
                totals = calculate_line_totals(
                    quantity=item.quantity,
                    rate=item.rate,
                    discount_percent=item.discount_percent,
                    tax_rate=item.tax_rate,
                )
                item.discount_amount = totals.discount_amount
                item.taxable_amount = totals.taxable_amount
                item.tax_amount = totals.tax_amount
                item.line_total = totals.line_total
                line_totals.append(totals)

            invoice_totals = calculate_invoice_totals(
                line_totals,
                transport_charge=invoice.transport_charge,
                other_charge=invoice.other_charge,
                round_off=invoice.round_off,
                paid_amount=invoice.paid_amount,
            )
        except FinancialCalculationError as exc:
            raise InvoiceCalculationError(str(exc)) from exc

        invoice.subtotal = invoice_totals.subtotal
        invoice.discount_amount = invoice_totals.discount_amount
        invoice.taxable_amount = invoice_totals.taxable_amount
        invoice.tax_amount = invoice_totals.tax_amount
        invoice.total_amount = invoice_totals.total_amount
        invoice.balance_amount = invoice_totals.balance_amount

    async def _ensure_trip_catch_and_fish_valid(
        self,
        trip_catch_id: uuid.UUID,
        fish_id: uuid.UUID,
        quantity: Decimal,
        *,
        tenant_id: uuid.UUID,
    ) -> TripCatchResponse:
        try:
            trip_catch = await self._trip_catch_service.get(trip_catch_id, tenant_id=tenant_id)
        except TripCatchNotFoundError as exc:
            raise InvoiceItemTripCatchNotFoundError(
                "The specified trip catch does not exist"
            ) from exc

        try:
            await self._fish_service.get(fish_id, tenant_id=tenant_id)
        except FishNotFoundError as exc:
            raise InvoiceItemFishNotFoundError("The specified fish does not exist") from exc

        if trip_catch.fish_id != fish_id:
            raise InvoiceItemFishMismatchError(
                "The specified fish does not match the trip catch's fish"
            )
        if quantity > trip_catch.available_quantity:
            raise InvoiceItemQuantityExceedsAvailableError(
                "Quantity exceeds the trip catch's available quantity"
            )
        return trip_catch

    async def _get_item_or_raise(
        self, invoice_id: uuid.UUID, item_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> InvoiceItem:
        item = await self._repo.get_item_by_id(item_id, invoice_id, tenant_id)
        if item is None:
            raise InvoiceItemNotFoundError("Invoice item not found")
        return item

    async def _ensure_company_active(
        self, company_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CompanyResponse:
        # CompanyService.get() is already tenant-scoped, so a company
        # belonging to another tenant surfaces as "not found" here too -
        # that's the correct behaviour for the "company must belong to the
        # current tenant" rule.
        try:
            company = await self._company_service.get(company_id, tenant_id=tenant_id)
        except CompanyNotFoundError as exc:
            raise InvoiceCompanyNotFoundError("The specified company does not exist") from exc
        if company.status != CompanyStatus.ACTIVE:
            raise InvoiceCompanyInactiveError("The specified company is not active")
        return company

    @staticmethod
    def _ensure_draft(invoice: Invoice) -> None:
        if invoice.status != InvoiceStatus.DRAFT:
            raise InvoiceNotDraftError("Only draft invoices can be edited or deleted")

    async def _get_or_raise(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> Invoice:
        invoice = await self._repo.get_by_id(invoice_id, tenant_id)
        if invoice is None:
            raise InvoiceNotFoundError("Invoice not found")
        return invoice

    async def _commit_or_raise(self) -> None:
        """Commit, translating an integrity violation into a clean error.

        Sessions 2-4's writes never assign invoice_number, so no unique
        constraint could fire from them; Session 5's issue() does assign
        one, but _allocate_invoice_number's `SELECT ... FOR UPDATE` locking
        already prevents a duplicate from ever being generated. This is
        the same defensive backstop every other module's service keeps for
        its own unique constraints, translating the (expected-unreachable)
        violation into InvoiceNumberConflictError instead of a raw 500.
        """
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        # asyncpg's UniqueViolationError (with .constraint_name) is chained as
        # __cause__ underneath SQLAlchemy's DBAPI-compatibility wrapper (.orig).
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_invoices_tenant_invoice_number":
            return InvoiceNumberConflictError(
                "This invoice number is already in use for this tenant"
            )
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(invoice: Invoice) -> InvoiceResponse:
        return InvoiceResponse.model_validate(invoice)

    @staticmethod
    def _to_item_response(item: InvoiceItem) -> InvoiceItemResponse:
        return InvoiceItemResponse.model_validate(item)
