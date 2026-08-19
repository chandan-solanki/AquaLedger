import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.core.errors import AppException, ConflictError
from app.modules.auth.models import Tenant
from app.modules.company_profile.service import CompanyProfileService
from app.modules.purchase_orders.constants import PURCHASE_ORDER_NUMBER_PREFIX, PurchaseOrderStatus
from app.modules.purchase_orders.domain.numbering import (
    fiscal_year_for,
    format_purchase_order_number,
)
from app.modules.purchase_orders.domain.totals import (
    FinancialCalculationError,
    LineTotals,
    calculate_line_totals,
    calculate_purchase_order_totals,
)
from app.modules.purchase_orders.exceptions import (
    PurchaseOrderCalculationError,
    PurchaseOrderDocumentNotAvailableError,
    PurchaseOrderEmptyError,
    PurchaseOrderInvalidTransitionError,
    PurchaseOrderItemNotFoundError,
    PurchaseOrderNotDraftError,
    PurchaseOrderNotFoundError,
    PurchaseOrderNumberConflictError,
    PurchaseOrderSupplierInactiveError,
    PurchaseOrderSupplierNotFoundError,
    PurchaseOrderTotalsInvalidError,
)
from app.modules.purchase_orders.models import PurchaseOrder, PurchaseOrderItem
from app.modules.purchase_orders.repository import PurchaseOrderRepository
from app.modules.purchase_orders.schemas import (
    PurchaseOrderCreateRequest,
    PurchaseOrderItemCreateRequest,
    PurchaseOrderItemResponse,
    PurchaseOrderItemUpdateRequest,
    PurchaseOrderListParams,
    PurchaseOrderResponse,
    PurchaseOrderUpdateRequest,
)
from app.modules.suppliers.constants import SupplierStatus
from app.modules.suppliers.exceptions import SupplierNotFoundError
from app.modules.suppliers.schemas import SupplierResponse
from app.modules.suppliers.service import SupplierService


class PurchaseOrderDocumentContext(NamedTuple):
    """Everything build_purchase_order_document_data() needs, already
    fetched and tenant-scoped by get_document_context() below - mirrors
    PurchaseBillDocumentContext exactly."""

    purchase_order: PurchaseOrderResponse
    items: list[PurchaseOrderItemResponse]
    supplier: SupplierResponse
    tenant_name: str
    tenant_details: str | None
    tenant_logo_bytes: bytes | None


class PurchaseOrderService:
    """Purchase order domain foundation (Sprint 12 Session 9 - TASKS.md),
    mirroring PurchaseService's shape closely: supplier validation goes
    through SupplierService only (never SupplierRepository directly,
    ARCHITECTURE.md §2), only DRAFT orders may be updated/deleted/have
    items mutated (PurchaseOrderNotDraftError), and every item mutation
    triggers _recalculate_purchase_order which delegates all math to
    app.modules.purchase_orders.domain.totals - never inline here.

    Unlike PurchaseService, a purchase order is not a financial document:
    confirm() (the draft -> confirmed transition, mirroring
    PurchaseService.post's number-allocation/immutability shape) never
    touches Supplier.outstanding_amount, ledger, or any financial report -
    a PO is a procurement commitment, not a bill. cancel() and fulfill()
    are the two further lifecycle transitions this module adds that
    PurchaseBill does not have yet (DRAFT|CONFIRMED -> CANCELLED,
    CONFIRMED -> FULFILLED), both simple status-only transitions with no
    side effects on any other module.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PurchaseOrderRepository(session)
        self._supplier_service = SupplierService(session)
        self._company_profile_service = CompanyProfileService(session)

    async def create(
        self, payload: PurchaseOrderCreateRequest, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PurchaseOrderResponse:
        await self._ensure_supplier_active(payload.supplier_id, tenant_id)

        # po_number/confirmed_at stay NULL and every financial field stays 0 -
        # none is client-supplied (see PurchaseOrderCreateRequest); the
        # number and totals are assigned by confirm()/item mutations.
        purchase_order = PurchaseOrder(
            tenant_id=tenant_id,
            supplier_id=payload.supplier_id,
            po_number=None,
            order_date=payload.order_date,
            expected_delivery_date=payload.expected_delivery_date,
            status=PurchaseOrderStatus.DRAFT,
            subtotal=0,
            discount_amount=0,
            taxable_amount=0,
            tax_amount=0,
            transport_charge=0,
            other_charge=0,
            round_off=0,
            total_amount=0,
            remarks=payload.remarks,
            confirmed_at=None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(purchase_order)
        await self._commit_or_raise()
        await self._session.refresh(purchase_order)
        return self._to_response(purchase_order)

    async def get(
        self, purchase_order_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> PurchaseOrderResponse:
        purchase_order = await self._get_or_raise(purchase_order_id, tenant_id)
        return self._to_response(purchase_order)

    async def get_for_update(
        self, purchase_order_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> PurchaseOrderResponse:
        """Same lookup as get(), but row-locks the order (`SELECT ... FOR
        UPDATE`) instead of a plain read. Used by PurchaseService.
        _validate_po_item_link so two concurrent bill-item add/update calls
        against items on the same order can't both read the "already
        billed" sum before either commits and jointly exceed an item's
        ordered quantity - mirrors the lock confirm()/cancel()/fulfill()
        already take, just without a status transition attached."""
        purchase_order = await self._repo.get_by_id_for_update(purchase_order_id, tenant_id)
        if purchase_order is None:
            raise PurchaseOrderNotFoundError("Purchase order not found")
        return self._to_response(purchase_order)

    async def list_purchase_orders(
        self, *, tenant_id: uuid.UUID, params: PurchaseOrderListParams
    ) -> PaginatedResponse[PurchaseOrderResponse]:
        # Supplier-name search is resolved through SupplierService (not a
        # repository join) - modules never import another module's ORM
        # model directly.
        q_supplier_ids: list[uuid.UUID] | None = None
        if params.q and params.q.strip():
            q_supplier_ids = await self._supplier_service.find_ids_by_name(tenant_id, params.q)

        purchase_orders, total = await self._repo.search(
            tenant_id,
            q=params.q,
            q_supplier_ids=q_supplier_ids,
            status=params.status,
            supplier_id=params.supplier_id,
            billable=params.billable,
            order_date_from=params.order_date_from,
            order_date_to=params.order_date_to,
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
            data=[self._to_response(order) for order in purchase_orders], meta=meta
        )

    async def update(
        self,
        purchase_order_id: uuid.UUID,
        payload: PurchaseOrderUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> PurchaseOrderResponse:
        purchase_order = await self._get_or_raise(purchase_order_id, tenant_id)
        self._ensure_draft(purchase_order)
        update_data = payload.model_dump(exclude_unset=True)

        new_supplier_id = update_data.get("supplier_id", purchase_order.supplier_id)
        if "supplier_id" in update_data and new_supplier_id != purchase_order.supplier_id:
            await self._ensure_supplier_active(new_supplier_id, tenant_id)

        for field, value in update_data.items():
            setattr(purchase_order, field, value)
        purchase_order.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(purchase_order)
        return self._to_response(purchase_order)

    async def delete(
        self, purchase_order_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        purchase_order = await self._get_or_raise(purchase_order_id, tenant_id)
        self._ensure_draft(purchase_order)
        purchase_order.deleted_at = datetime.now(UTC)
        purchase_order.deleted_by = actor_id
        await self._session.commit()

    async def add_item(
        self,
        purchase_order_id: uuid.UUID,
        payload: PurchaseOrderItemCreateRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> PurchaseOrderItemResponse:
        purchase_order = await self._get_or_raise(purchase_order_id, tenant_id)
        self._ensure_draft(purchase_order)
        line_number = await self._repo.allocate_next_line_number(purchase_order_id, tenant_id)

        # Financial columns start at zero - none is client-supplied (see
        # PurchaseOrderItemCreateRequest) - and are immediately overwritten
        # by _recalculate_purchase_order below.
        item = PurchaseOrderItem(
            tenant_id=tenant_id,
            purchase_order_id=purchase_order_id,
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
        await self._recalculate_purchase_order(purchase_order, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(item)
        return self._to_item_response(item)

    async def list_items(
        self,
        purchase_order_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
        q: str | None,
        sort: str,
    ) -> list[PurchaseOrderItemResponse]:
        # Listing is allowed regardless of order status - only add/edit/
        # delete are restricted to DRAFT.
        await self._get_or_raise(purchase_order_id, tenant_id)
        items = await self._repo.search_items(purchase_order_id, tenant_id, q=q, sort=sort)
        return [self._to_item_response(item) for item in items]

    async def update_item(
        self,
        purchase_order_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: PurchaseOrderItemUpdateRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> PurchaseOrderItemResponse:
        purchase_order = await self._get_or_raise(purchase_order_id, tenant_id)
        self._ensure_draft(purchase_order)
        item = await self._get_item_or_raise(purchase_order_id, item_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(item, field, value)
        await self._session.flush()
        await self._recalculate_purchase_order(purchase_order, tenant_id)
        await self._commit_or_raise()
        await self._session.refresh(item)
        return self._to_item_response(item)

    async def delete_item(
        self, purchase_order_id: uuid.UUID, item_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        purchase_order = await self._get_or_raise(purchase_order_id, tenant_id)
        self._ensure_draft(purchase_order)
        item = await self._get_item_or_raise(purchase_order_id, item_id, tenant_id)
        await self._repo.delete_item(item)
        await self._session.flush()
        await self._recalculate_purchase_order(purchase_order, tenant_id)
        await self._commit_or_raise()

    async def confirm(
        self, purchase_order_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PurchaseOrderResponse:
        """The draft -> confirmed transition - irreversibly assigns
        `po_number` and freezes the order's editable window, all inside
        one transaction. Mirrors PurchaseService.post's shape exactly
        except it never touches Supplier.outstanding_amount: a confirmed
        purchase order is a procurement commitment, not a payable, so it
        must stay financially inert (the task's explicit hard requirement).

        Order of operations:
        1. Lock the purchase order row (`SELECT ... FOR UPDATE`) - this
           alone is what makes a concurrent double-confirm impossible.
        2. Must be DRAFT - this single check also covers "cannot confirm
           twice" and "cannot confirm a cancelled/fulfilled order".
        3. Must have at least one item (PurchaseOrderEmptyError).
        4. Recalculate every total from scratch immediately before
           confirming (never trust whatever was last persisted).
        5. Generate the PO number only after totals validate.
        6. Mark CONFIRMED, stamp confirmed_at.
        7. Commit.
        """
        try:
            purchase_order = await self._repo.get_by_id_for_update(purchase_order_id, tenant_id)
            if purchase_order is None:
                raise PurchaseOrderNotFoundError("Purchase order not found")
            self._ensure_draft(purchase_order)

            items = await self._repo.search_items(
                purchase_order.id, tenant_id, q=None, sort="line_number"
            )
            if not items:
                raise PurchaseOrderEmptyError(
                    "A purchase order must have at least one item to be confirmed"
                )

            try:
                await self._recalculate_purchase_order(purchase_order, tenant_id)
            except PurchaseOrderCalculationError as exc:
                raise PurchaseOrderTotalsInvalidError(str(exc)) from exc

            purchase_order.po_number = await self._allocate_purchase_order_number(
                purchase_order, tenant_id
            )
            purchase_order.status = PurchaseOrderStatus.CONFIRMED
            purchase_order.confirmed_at = datetime.now(UTC)
            purchase_order.updated_by = actor_id
        except Exception:
            await self._session.rollback()
            raise

        await self._commit_or_raise()
        await self._session.refresh(purchase_order)
        return self._to_response(purchase_order)

    async def cancel(
        self, purchase_order_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PurchaseOrderResponse:
        """DRAFT|CONFIRMED -> CANCELLED. No side effects on any other
        module - a cancelled purchase order never affected
        Supplier.outstanding_amount/ledger in the first place, so there is
        nothing to reverse."""
        purchase_order = await self._repo.get_by_id_for_update(purchase_order_id, tenant_id)
        if purchase_order is None:
            raise PurchaseOrderNotFoundError("Purchase order not found")
        if purchase_order.status not in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.CONFIRMED):
            raise PurchaseOrderInvalidTransitionError(
                "Only draft or confirmed purchase orders can be cancelled"
            )
        purchase_order.status = PurchaseOrderStatus.CANCELLED
        purchase_order.updated_by = actor_id
        await self._session.commit()
        await self._session.refresh(purchase_order)
        return self._to_response(purchase_order)

    async def fulfill(
        self, purchase_order_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> PurchaseOrderResponse:
        """CONFIRMED -> FULFILLED. This is simply the PO lifecycle
        foundation - it does not create Purchase Bills, does not create
        payment records, and does not modify supplier outstanding.
        Partial fulfillment and the Purchase Bill linkage are deferred to
        a future integration session."""
        purchase_order = await self._repo.get_by_id_for_update(purchase_order_id, tenant_id)
        if purchase_order is None:
            raise PurchaseOrderNotFoundError("Purchase order not found")
        if purchase_order.status != PurchaseOrderStatus.CONFIRMED:
            raise PurchaseOrderInvalidTransitionError(
                "Only confirmed purchase orders can be fulfilled"
            )
        purchase_order.status = PurchaseOrderStatus.FULFILLED
        purchase_order.updated_by = actor_id
        await self._session.commit()
        await self._session.refresh(purchase_order)
        return self._to_response(purchase_order)

    async def get_document_context(
        self, purchase_order_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> PurchaseOrderDocumentContext:
        """Bundles the purchase order, its items, its supplier and the
        tenant's display name for GET /{id}/document (Sprint 12 Session 11) -
        mirrors PurchaseService.get_document_context exactly. A purchase
        order only has a po_number once confirmed (or confirmed-then-
        cancelled) - one still DRAFT, or cancelled directly from DRAFT, has
        nothing to print.
        """
        purchase_order = await self._get_or_raise(purchase_order_id, tenant_id)
        if purchase_order.po_number is None:
            raise PurchaseOrderDocumentNotAvailableError(
                "The purchase order must be confirmed before its document can be generated"
            )

        items = await self._repo.search_items(
            purchase_order.id, tenant_id, q=None, sort="line_number"
        )

        try:
            supplier = await self._supplier_service.get(
                purchase_order.supplier_id, tenant_id=tenant_id
            )
        except SupplierNotFoundError as exc:
            raise PurchaseOrderSupplierNotFoundError(
                "The specified supplier does not exist"
            ) from exc

        tenant_name = await self._get_tenant_name(tenant_id)
        profile_context = await self._company_profile_service.get_document_context(tenant_id)

        return PurchaseOrderDocumentContext(
            purchase_order=self._to_response(purchase_order),
            items=[self._to_item_response(item) for item in items],
            supplier=supplier,
            tenant_name=profile_context.display_name or tenant_name,
            tenant_details=profile_context.tenant_details,
            tenant_logo_bytes=profile_context.logo_bytes,
        )

    async def _get_tenant_name(self, tenant_id: uuid.UUID) -> str:
        result = await self._session.execute(select(Tenant.name).where(Tenant.id == tenant_id))
        return result.scalar_one()

    async def _allocate_purchase_order_number(
        self, purchase_order: PurchaseOrder, tenant_id: uuid.UUID
    ) -> str:
        """Concurrency-safe sequential number allocation: `INSERT ... ON
        CONFLICT DO NOTHING` guarantees the per-tenant/prefix/fiscal-year
        counter row exists without racing a concurrent first allocation for
        that fiscal year, then `SELECT ... FOR UPDATE` locks it so the
        increment below can never be lost to a concurrent confirm. Only
        called from confirm(), already inside its transaction. Mirrors
        PurchaseService._allocate_purchase_number exactly."""
        fiscal_year = fiscal_year_for(purchase_order.order_date)
        await self._repo.ensure_sequence_row(tenant_id, PURCHASE_ORDER_NUMBER_PREFIX, fiscal_year)
        sequence = await self._repo.get_sequence_for_update(
            tenant_id, PURCHASE_ORDER_NUMBER_PREFIX, fiscal_year
        )
        sequence.last_number += 1
        return format_purchase_order_number(
            PURCHASE_ORDER_NUMBER_PREFIX, fiscal_year, sequence.last_number
        )

    async def get_item(
        self, purchase_order_id: uuid.UUID, item_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> PurchaseOrderItemResponse:
        """Public, tenant-scoped single-item lookup (Sprint 12 Session 12) -
        used by PurchaseService to resolve/validate a purchase bill item's
        purchase_order_item_id. Scoped by both purchase_order_id and
        item_id together, so an item belonging to a different order is
        indistinguishable from "does not exist" - the caller translates
        PurchaseOrderItemNotFoundError into its own
        PurchaseBillPurchaseOrderItemNotFoundError."""
        item = await self._get_item_or_raise(purchase_order_id, item_id, tenant_id)
        return self._to_item_response(item)

    async def _get_item_or_raise(
        self, purchase_order_id: uuid.UUID, item_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseOrderItem:
        item = await self._repo.get_item_by_id(item_id, purchase_order_id, tenant_id)
        if item is None:
            raise PurchaseOrderItemNotFoundError("Purchase order item not found")
        return item

    async def _recalculate_purchase_order(
        self, purchase_order: PurchaseOrder, tenant_id: uuid.UUID
    ) -> None:
        """Recomputes every item's discount_amount/taxable_amount/
        tax_amount/line_total and every order-level financial total from
        scratch, via app.modules.purchase_orders.domain.totals - never
        inline here. Called after every mutation that could change them:
        item added, updated, or deleted.

        Callers must `await self._session.flush()` first - this app's
        session factory sets `autoflush=False` (app.db.session), so
        without an explicit flush this method's read of the item list
        would miss whatever the caller just added/changed/deleted.
        """
        items = await self._repo.search_items(
            purchase_order.id, tenant_id, q=None, sort="line_number"
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

            order_totals = calculate_purchase_order_totals(
                line_totals,
                transport_charge=purchase_order.transport_charge,
                other_charge=purchase_order.other_charge,
                round_off=purchase_order.round_off,
            )
        except FinancialCalculationError as exc:
            raise PurchaseOrderCalculationError(str(exc)) from exc

        purchase_order.subtotal = order_totals.subtotal
        purchase_order.discount_amount = order_totals.discount_amount
        purchase_order.taxable_amount = order_totals.taxable_amount
        purchase_order.tax_amount = order_totals.tax_amount
        purchase_order.total_amount = order_totals.total_amount

    async def _ensure_supplier_active(
        self, supplier_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SupplierResponse:
        # SupplierService.get() is already tenant-scoped, so a supplier
        # belonging to another tenant surfaces as "not found" here too.
        try:
            supplier = await self._supplier_service.get(supplier_id, tenant_id=tenant_id)
        except SupplierNotFoundError as exc:
            raise PurchaseOrderSupplierNotFoundError(
                "The specified supplier does not exist"
            ) from exc
        if supplier.status != SupplierStatus.ACTIVE:
            raise PurchaseOrderSupplierInactiveError("The specified supplier is not active")
        return supplier

    @staticmethod
    def _ensure_draft(purchase_order: PurchaseOrder) -> None:
        if purchase_order.status != PurchaseOrderStatus.DRAFT:
            raise PurchaseOrderNotDraftError(
                "Only draft purchase orders can be edited, deleted, or confirmed"
            )

    async def _get_or_raise(
        self, purchase_order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PurchaseOrder:
        purchase_order = await self._repo.get_by_id(purchase_order_id, tenant_id)
        if purchase_order is None:
            raise PurchaseOrderNotFoundError("Purchase order not found")
        return purchase_order

    async def _commit_or_raise(self) -> None:
        """Commit, translating a unique-constraint violation into a clean
        409 - the same race-avoidance rationale PurchaseService gives for
        its own unique constraints."""
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_purchase_orders_tenant_po_number":
            return PurchaseOrderNumberConflictError(
                "This PO number is already in use for this tenant"
            )
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(purchase_order: PurchaseOrder) -> PurchaseOrderResponse:
        return PurchaseOrderResponse.model_validate(purchase_order)

    @staticmethod
    def _to_item_response(item: PurchaseOrderItem) -> PurchaseOrderItemResponse:
        return PurchaseOrderItemResponse.model_validate(item)
