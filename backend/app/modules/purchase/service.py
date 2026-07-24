import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.purchase.constants import PURCHASE_NUMBER_PREFIX, PurchaseStatus
from app.modules.purchase.domain.numbering import fiscal_year_for, format_purchase_number
from app.modules.purchase.domain.totals import (
    FinancialCalculationError,
    LineTotals,
    calculate_line_totals,
    calculate_purchase_bill_totals,
)
from app.modules.purchase.exceptions import (
    PurchaseBillEmptyError,
    PurchaseBillItemNotFoundError,
    PurchaseBillNotDraftError,
    PurchaseBillNotFoundError,
    PurchaseBillReconciliationError,
    PurchaseBillSupplierInactiveError,
    PurchaseBillSupplierNotFoundError,
    PurchaseCalculationError,
    PurchaseNumberConflictError,
    PurchaseTotalsInvalidError,
)
from app.modules.purchase.models import PurchaseBill, PurchaseBillItem
from app.modules.purchase.repository import PurchaseRepository
from app.modules.purchase.schemas import (
    PurchaseBillCreateRequest,
    PurchaseBillItemCreateRequest,
    PurchaseBillItemResponse,
    PurchaseBillItemUpdateRequest,
    PurchaseBillListParams,
    PurchaseBillResponse,
    PurchaseBillUpdateRequest,
)
from app.modules.supplier_payments.domain.reconciliation import (
    ReconciliationError,
    calculate_purchase_bill_payment,
)
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.exceptions import SupplierNotFoundError
from app.modules.suppliers.schemas import SupplierResponse
from app.modules.suppliers.service import SupplierService


class PurchaseService:
    """Sprint 11 Session 2 - draft purchase bill CRUD (TASKS.md), mirroring
    InvoiceService/PaymentService's own Session 2 shape: every financial
    field is fixed at 0/DRAFT/NULL (no calculation engine or numbering
    yet - those land in Sessions 4/5), and only DRAFT bills may be updated
    or deleted (PurchaseBillNotDraftError).

    Supplier validation goes through SupplierService only - never
    SupplierRepository directly (ARCHITECTURE.md §2, TASKS.md's explicit
    instruction for this session).

    Session 3 (TASKS.md) adds purchase bill item CRUD (add_item/list_items/
    update_item/delete_item), same DRAFT-only mutation rule as the bill
    itself.

    Session 4 adds the financial engine: every item mutation (add/update/
    delete) triggers _recalculate_purchase_bill, which delegates all math to
    app.modules.purchase.domain.totals - never inline here (TASKS.md
    Session 4: "PurchaseService owns recalculation. Call pure domain
    functions only.").

    Session 5 adds post() - the core business transaction of this module,
    mirroring InvoiceService.issue: draft -> posted, irreversible, assigns
    bill_number (app.modules.purchase.domain.numbering) and increases the
    supplier's outstanding_amount (via SupplierService, never
    SupplierRepository directly), all inside one transaction. Every other
    method in this class enforces DRAFT-only mutation (_ensure_draft) as
    the immutability half of that same rule.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PurchaseRepository(session)
        self._supplier_service = SupplierService(session)

    async def create(
        self, payload: PurchaseBillCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PurchaseBillResponse:
        await self._ensure_supplier_active(payload.supplier_id, tenant_id)

        # bill_number/posted_at stay NULL and every financial field stays 0 -
        # none is client-supplied (see PurchaseBillCreateRequest); numbers
        # and totals are assigned in future sessions.
        purchase_bill = PurchaseBill(
            tenant_id=tenant_id,
            supplier_id=payload.supplier_id,
            bill_number=None,
            bill_date=payload.bill_date,
            due_date=payload.due_date,
            status=PurchaseStatus.DRAFT,
            subtotal=0,
            discount_amount=0,
            taxable_amount=0,
            tax_amount=0,
            transport_charge=0,
            other_charge=0,
            round_off=0,
            total_amount=0,
            paid_amount=0,
            balance_amount=0,
            remarks=payload.remarks,
            posted_at=None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(purchase_bill)
        await self._commit_or_raise()
        await self._session.refresh(purchase_bill)
        return self._to_response(purchase_bill)

    async def get(
        self, purchase_bill_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> PurchaseBillResponse:
        purchase_bill = await self._get_or_raise(purchase_bill_id, tenant_id)
        return self._to_response(purchase_bill)

    async def list_purchase_bills(
        self, *, tenant_id: uuid.UUID, params: PurchaseBillListParams
    ) -> PaginatedResponse[PurchaseBillResponse]:
        # Supplier-name search is resolved through SupplierService (not a
        # repository join) - modules never import another module's ORM
        # model directly.
        q_supplier_ids: list[uuid.UUID] | None = None
        if params.q and params.q.strip():
            q_supplier_ids = await self._supplier_service.find_ids_by_name(tenant_id, params.q)

        purchase_bills, total = await self._repo.search(
            tenant_id,
            q=params.q,
            q_supplier_ids=q_supplier_ids,
            status=params.status,
            supplier_id=params.supplier_id,
            bill_date_from=params.bill_date_from,
            bill_date_to=params.bill_date_to,
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
            data=[self._to_response(bill) for bill in purchase_bills], meta=meta
        )

    async def update(
        self,
        purchase_bill_id: uuid.UUID,
        payload: PurchaseBillUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> PurchaseBillResponse:
        purchase_bill = await self._get_or_raise(purchase_bill_id, tenant_id)
        self._ensure_draft(purchase_bill)
        update_data = payload.model_dump(exclude_unset=True)

        new_supplier_id = update_data.get("supplier_id", purchase_bill.supplier_id)
        if "supplier_id" in update_data and new_supplier_id != purchase_bill.supplier_id:
            await self._ensure_supplier_active(new_supplier_id, tenant_id)

        for field, value in update_data.items():
            setattr(purchase_bill, field, value)
        purchase_bill.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(purchase_bill)
        return self._to_response(purchase_bill)

    async def delete(
        self, purchase_bill_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        purchase_bill = await self._get_or_raise(purchase_bill_id, tenant_id)
        self._ensure_draft(purchase_bill)
        purchase_bill.deleted_at = datetime.now(UTC)
        purchase_bill.deleted_by = actor_id
        await self._session.commit()

    async def add_item(
        self,
        purchase_bill_id: uuid.UUID,
        payload: PurchaseBillItemCreateRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> PurchaseBillItemResponse:
        purchase_bill = await self._get_or_raise(purchase_bill_id, tenant_id)
        self._ensure_draft(purchase_bill)
        line_number = await self._repo.allocate_next_line_number(purchase_bill_id, tenant_id)

        # Financial columns start at zero - none is client-supplied (see
        # PurchaseBillItemCreateRequest) - and are immediately overwritten
        # by _recalculate_purchase_bill below, which computes this item's
        # real discount_amount/taxable_amount/tax_amount/line_total
        # (app.modules.purchase.domain.totals) along with the bill's
        # aggregate totals.
        item = PurchaseBillItem(
            tenant_id=tenant_id,
            purchase_bill_id=purchase_bill_id,
            line_number=line_number,
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
        )
        await self._repo.add_item(item)
        await self._session.flush()
        await self._recalculate_purchase_bill(purchase_bill, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(item)
        return self._to_item_response(item)

    async def list_items(
        self,
        purchase_bill_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
        q: str | None,
        sort: str,
    ) -> list[PurchaseBillItemResponse]:
        # Listing is allowed regardless of bill status - only add/edit/
        # delete are restricted to DRAFT.
        await self._get_or_raise(purchase_bill_id, tenant_id)
        items = await self._repo.search_items(purchase_bill_id, tenant_id, q=q, sort=sort)
        return [self._to_item_response(item) for item in items]

    async def update_item(
        self,
        purchase_bill_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: PurchaseBillItemUpdateRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> PurchaseBillItemResponse:
        purchase_bill = await self._get_or_raise(purchase_bill_id, tenant_id)
        self._ensure_draft(purchase_bill)
        item = await self._get_item_or_raise(purchase_bill_id, item_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(item, field, value)
        await self._session.flush()
        await self._recalculate_purchase_bill(purchase_bill, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(item)
        return self._to_item_response(item)

    async def delete_item(
        self, purchase_bill_id: uuid.UUID, item_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        purchase_bill = await self._get_or_raise(purchase_bill_id, tenant_id)
        self._ensure_draft(purchase_bill)
        item = await self._get_item_or_raise(purchase_bill_id, item_id, tenant_id)
        await self._repo.delete_item(item)
        await self._session.flush()
        await self._recalculate_purchase_bill(purchase_bill, tenant_id)
        await self._commit_or_raise()

    async def post(
        self, purchase_bill_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PurchaseBillResponse:
        """The core business transaction of this module (TASKS.md Session
        5) - draft -> posted, immutable from this point on. Everything
        below runs inside one transaction, committed only at the very end;
        any failure at any step rolls back all of it together (the
        purchase bill, its items' recalculated totals, and the supplier's
        outstanding_amount).

        Order of operations:
        1. Lock the purchase bill row (`SELECT ... FOR UPDATE`) - this alone
           is what makes a concurrent double-post impossible, not just the
           DRAFT check below (two requests both reading status == draft
           before either writes would otherwise both proceed).
        2/3. get_by_id_for_update already scopes by tenant_id, so "does not
           exist" and "belongs to another tenant" are the same 404.
        4. Must be DRAFT - this single check also covers "cannot post
           twice" (status is already POSTED) and "cannot post a cancelled
           bill" (status is CANCELLED), the same guard every other
           mutating method here uses for immutability.
        5. Must have at least one item (PurchaseBillEmptyError).
        6. Recalculate every total from scratch immediately before posting
           (never trust whatever was last persisted), via the same
           _recalculate_purchase_bill/domain.totals engine every item
           mutation uses. Its FinancialCalculationError is translated to
           PurchaseTotalsInvalidError here rather than PurchaseCalculationError
           - a distinct code for a failure specifically at posting time
           (TASKS.md Session 5's explicit "Validate totals" step).
        7. Generate the purchase number only after totals validate - not
           required for correctness (the whole transaction rolls back
           together regardless of ordering), but avoids burning a number on
           an attempt that was always going to fail.
        8. Mark POSTED, stamp posted_at, set bill_number.
        9. Increase the supplier's outstanding_amount by balance_amount -
           a single atomic UPDATE (SupplierRepository.increase_outstanding_amount),
           never a Python read-modify-write.
        10. Commit.

        Any failure at any step - including one raised after an earlier
        step's `flush()` has already sent writes to the database within
        this transaction - triggers an explicit rollback before the
        exception propagates, mirroring InvoiceService.issue exactly.

        Explicitly not implemented (TASKS.md: "Do NOT implement"):
        supplier payments, ledger entries, PDF generation, notifications,
        inventory, journal entries.
        """
        try:
            purchase_bill = await self._repo.get_by_id_for_update(purchase_bill_id, tenant_id)
            if purchase_bill is None:
                raise PurchaseBillNotFoundError("Purchase bill not found")
            self._ensure_draft(purchase_bill)

            items = await self._repo.search_items(
                purchase_bill.id, tenant_id, q=None, sort="line_number"
            )
            if not items:
                raise PurchaseBillEmptyError(
                    "A purchase bill must have at least one item to be posted"
                )

            try:
                await self._recalculate_purchase_bill(purchase_bill, tenant_id)
            except PurchaseCalculationError as exc:
                raise PurchaseTotalsInvalidError(str(exc)) from exc

            purchase_bill.bill_number = await self._allocate_purchase_number(
                purchase_bill, tenant_id
            )
            purchase_bill.status = PurchaseStatus.POSTED
            purchase_bill.posted_at = datetime.now(UTC)
            purchase_bill.updated_by = actor_id

            await self._supplier_service.increase_outstanding(
                purchase_bill.supplier_id, purchase_bill.balance_amount, tenant_id=tenant_id
            )
        except Exception:
            await self._session.rollback()
            raise

        await self._commit_or_raise()
        await self._session.refresh(purchase_bill)
        return self._to_response(purchase_bill)

    async def recalculate_payment_totals(
        self, purchase_bill_id: uuid.UUID, *, tenant_id: uuid.UUID, total_allocated: Decimal
    ) -> None:
        """Sprint 12 Session 4's outstanding engine: recomputes this
        purchase bill's paid_amount/balance_amount/status from scratch
        (app.modules.supplier_payments.domain.reconciliation.calculate_purchase_bill_payment)
        and then cascades into recomputing its supplier's outstanding_amount -
        never patched incrementally, the same recompute-from-source
        discipline _recalculate_purchase_bill applies to item totals.

        `total_allocated` is the sum of every currently-active allocation
        against this purchase bill, across every supplier payment - computed
        and passed in by SupplierPaymentService (via its own
        SupplierPaymentRepository; PurchaseService never touches the
        supplier_payments module's tables, ARCHITECTURE.md §2). Called after
        every allocation create/update/delete that touches this purchase
        bill (mirrors InvoiceService.recalculate_payment_totals exactly).
        """
        purchase_bill = await self._get_or_raise(purchase_bill_id, tenant_id)
        try:
            totals = calculate_purchase_bill_payment(
                total_amount=purchase_bill.total_amount,
                total_allocated=total_allocated,
                current_status=purchase_bill.status,
            )
        except ReconciliationError as exc:
            raise PurchaseBillReconciliationError(str(exc)) from exc

        purchase_bill.paid_amount = totals.paid_amount
        purchase_bill.balance_amount = totals.balance_amount
        purchase_bill.status = totals.status
        await self._session.flush()

        total_open_balance = await self._repo.sum_open_balance_by_supplier(
            purchase_bill.supplier_id, tenant_id
        )
        await self._supplier_service.recalculate_outstanding(
            purchase_bill.supplier_id, tenant_id=tenant_id, total_open_balance=total_open_balance
        )

    async def _allocate_purchase_number(
        self, purchase_bill: PurchaseBill, tenant_id: uuid.UUID
    ) -> str:
        """Concurrency-safe sequential number allocation: `INSERT ... ON
        CONFLICT DO NOTHING` guarantees the per-tenant/prefix/fiscal-year
        counter row exists without racing a concurrent first allocation for
        that fiscal year, then `SELECT ... FOR UPDATE` locks it so the
        increment below can never be lost to a concurrent post. Only
        called from post(), already inside its transaction - the row lock
        is held until that transaction commits or rolls back, serializing
        concurrent posts within one tenant/prefix/fiscal-year. Mirrors
        InvoiceService._allocate_invoice_number exactly."""
        fiscal_year = fiscal_year_for(purchase_bill.bill_date)
        await self._repo.ensure_sequence_row(tenant_id, PURCHASE_NUMBER_PREFIX, fiscal_year)
        sequence = await self._repo.get_sequence_for_update(
            tenant_id, PURCHASE_NUMBER_PREFIX, fiscal_year
        )
        sequence.last_number += 1
        return format_purchase_number(PURCHASE_NUMBER_PREFIX, fiscal_year, sequence.last_number)

    async def _get_item_or_raise(
        self, purchase_bill_id: uuid.UUID, item_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseBillItem:
        item = await self._repo.get_item_by_id(item_id, purchase_bill_id, tenant_id)
        if item is None:
            raise PurchaseBillItemNotFoundError("Purchase bill item not found")
        return item

    async def _recalculate_purchase_bill(
        self, purchase_bill: PurchaseBill, tenant_id: uuid.UUID
    ) -> None:
        """Recomputes every item's discount_amount/taxable_amount/
        tax_amount/line_total and every bill-level financial total from
        scratch, via app.modules.purchase.domain.totals - never inline here
        (TASKS.md Session 4: "Never patch totals. Always recompute from all
        active items."). Called after every mutation that could change them:
        item added, updated, or deleted.

        Recomputing every item unconditionally - not only the one that
        changed - is deliberate: each item's line totals are a pure
        function of its own quantity/rate/discount_percent/tax_rate, so
        this can never drift into a stale value, and a purchase bill's item
        count is small enough that the extra writes are negligible. Mirrors
        InvoiceService._recalculate_invoice exactly.

        Callers must `await self._session.flush()` first - this app's
        session factory sets `autoflush=False` (app.db.session), so without
        an explicit flush this method's read of the item list would miss
        whatever the caller just added/changed/deleted.
        """
        items = await self._repo.search_items(
            purchase_bill.id, tenant_id, q=None, sort="line_number"
        )

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

            bill_totals = calculate_purchase_bill_totals(
                line_totals,
                transport_charge=purchase_bill.transport_charge,
                other_charge=purchase_bill.other_charge,
                round_off=purchase_bill.round_off,
            )
        except FinancialCalculationError as exc:
            raise PurchaseCalculationError(str(exc)) from exc

        purchase_bill.subtotal = bill_totals.subtotal
        purchase_bill.discount_amount = bill_totals.discount_amount
        purchase_bill.taxable_amount = bill_totals.taxable_amount
        purchase_bill.tax_amount = bill_totals.tax_amount
        purchase_bill.total_amount = bill_totals.total_amount
        purchase_bill.paid_amount = bill_totals.paid_amount
        purchase_bill.balance_amount = bill_totals.balance_amount

    async def _ensure_supplier_active(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierResponse:
        # SupplierService.get() is already tenant-scoped, so a supplier
        # belonging to another tenant surfaces as "not found" here too -
        # that's the correct behaviour for the "supplier must belong to
        # the current tenant" rule (mirrors PaymentService._ensure_company_active).
        try:
            supplier = await self._supplier_service.get(supplier_id, tenant_id=tenant_id)
        except SupplierNotFoundError as exc:
            raise PurchaseBillSupplierNotFoundError(
                "The specified supplier does not exist"
            ) from exc
        if supplier.status != SupplierStatus.ACTIVE:
            raise PurchaseBillSupplierInactiveError("The specified supplier is not active")
        return supplier

    @staticmethod
    def _ensure_draft(purchase_bill: PurchaseBill) -> None:
        if purchase_bill.status != PurchaseStatus.DRAFT:
            raise PurchaseBillNotDraftError("Only draft purchase bills can be edited or deleted")

    async def _get_or_raise(
        self, purchase_bill_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseBill:
        purchase_bill = await self._repo.get_by_id(purchase_bill_id, tenant_id)
        if purchase_bill is None:
            raise PurchaseBillNotFoundError("Purchase bill not found")
        return purchase_bill

    async def _commit_or_raise(self) -> None:
        """Commit, translating a unique-constraint violation into a clean
        409 - the same race-avoidance rationale CompanyService/
        PaymentService give for their own unique constraints. Should be
        unreachable in practice now that Session 5's post() allocates
        bill_number under a locked sequence row, but remains as the same
        defensive backstop InvoiceService/PaymentService keep for their own
        number columns.
        """
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_purchase_bills_tenant_bill_number":
            return PurchaseNumberConflictError("This bill number is already in use for this tenant")
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(purchase_bill: PurchaseBill) -> PurchaseBillResponse:
        return PurchaseBillResponse.model_validate(purchase_bill)

    @staticmethod
    def _to_item_response(item: PurchaseBillItem) -> PurchaseBillItemResponse:
        return PurchaseBillItemResponse.model_validate(item)
