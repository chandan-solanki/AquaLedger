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
from app.modules.companies.exceptions import CompanyNotFoundError
from app.modules.companies.schemas import CompanyResponse
from app.modules.companies.service import CompanyService
from app.modules.company_profile.service import CompanyProfileService
from app.modules.delivery_challans.constants import (
    DELIVERY_CHALLAN_NUMBER_PREFIX,
    DeliveryChallanStatus,
)
from app.modules.delivery_challans.domain.numbering import (
    fiscal_year_for,
    format_delivery_challan_number,
)
from app.modules.delivery_challans.exceptions import (
    DeliveryChallanCompanyNotFoundError,
    DeliveryChallanDocumentNotAvailableError,
    DeliveryChallanEmptyError,
    DeliveryChallanFishNotFoundError,
    DeliveryChallanInvalidTransitionError,
    DeliveryChallanInvoiceItemNotFoundError,
    DeliveryChallanInvoiceNotDeliverableError,
    DeliveryChallanInvoiceNotFoundError,
    DeliveryChallanItemNotFoundError,
    DeliveryChallanNotDraftError,
    DeliveryChallanNotFoundError,
    DeliveryChallanNumberConflictError,
    DeliveryChallanOverDeliveryError,
)
from app.modules.delivery_challans.models import DeliveryChallan, DeliveryChallanItem
from app.modules.delivery_challans.repository import DeliveryChallanRepository
from app.modules.delivery_challans.schemas import (
    DeliveryChallanCreateRequest,
    DeliveryChallanItemCreateRequest,
    DeliveryChallanItemResponse,
    DeliveryChallanItemUpdateRequest,
    DeliveryChallanListParams,
    DeliveryChallanResponse,
    DeliveryChallanUpdateRequest,
)
from app.modules.fish.exceptions import FishNotFoundError
from app.modules.fish.schemas import FishResponse
from app.modules.fish.service import FishService
from app.modules.invoices.constants import InvoiceStatus
from app.modules.invoices.exceptions import InvoiceNotFoundError
from app.modules.invoices.schemas import InvoiceItemResponse, InvoiceResponse
from app.modules.invoices.service import InvoiceService

_DELIVERABLE_INVOICE_STATUSES = (
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.PAID,
)


class DeliveryChallanDocumentContext(NamedTuple):
    """Everything build_delivery_challan_document_data() (Sprint 12 Session
    16) needs, assembled by DeliveryChallanService.get_document_context() -
    mirrors PurchaseOrderDocumentContext/InvoiceDocumentContext's own
    labeled-NamedTuple shape.

    `previously_delivered_by_item_id` maps each of this challan's own
    DeliveryChallanItem ids to the quantity already delivered against that
    same invoice item by every OTHER non-cancelled delivery challan line
    (this item's own contribution subtracted back out) - reusing
    DeliveryChallanRepository.sum_delivered_by_invoice_items exactly (the
    same reservation-aware aggregation _validate_invoice_item_link's own
    over-delivery check already relies on), never a second, independently
    computed aggregation."""

    delivery_challan: DeliveryChallanResponse
    items: list[DeliveryChallanItemResponse]
    invoice: InvoiceResponse
    invoice_items_by_id: dict[uuid.UUID, InvoiceItemResponse]
    fish_by_id: dict[uuid.UUID, FishResponse]
    previously_delivered_by_item_id: dict[uuid.UUID, Decimal]
    company: CompanyResponse
    tenant_name: str
    tenant_details: str | None
    tenant_logo_bytes: bytes | None


class DeliveryChallanService:
    """Delivery challan domain foundation (Sprint 12 Session 14). A delivery
    challan records the physical dispatch/delivery of goods already invoiced
    to a customer - it is deliberately NOT a financial document: nothing in
    this file ever touches Company.outstanding_amount, Invoice.balance_amount/
    paid_amount, ledger, or any financial report. The financial event remains
    exclusively Invoice.issue() (creates the receivable) and Payment
    allocation (reduces it) - this module only ever reads an invoice's
    status/items, never writes to it.

    Only DRAFT challans may be updated/deleted/have items mutated
    (DeliveryChallanNotDraftError) - `dispatch()` (draft -> dispatched,
    assigns challan_number) and `deliver()` (dispatched -> delivered,
    terminal) are the two further lifecycle transitions, plus `cancel()`
    (draft|dispatched -> cancelled). Mirrors PurchaseOrderService's shape
    closely, with one deliberate structural difference: `invoice_id` is
    required, not optional, and there is no financial engine at all (see
    DeliveryChallan's own model docstring for why).

    Depends on InvoiceService only - never InvoiceRepository directly
    (ARCHITECTURE.md §2). delivery_challans is the downstream consumer;
    invoices has no dependency back on this module, so this is a one-
    directional edge, never a cycle. No new methods were added to
    InvoiceService for this - InvoiceService.get()/list_items() (both
    already public and tenant-scoped) are sufficient.
    """

    def __init__(self, session: AsyncSession, invoice_service: InvoiceService) -> None:
        self._session = session
        self._repo = DeliveryChallanRepository(session)
        self._invoice_service = invoice_service
        # Cross-module reference validation/lookups go through the other
        # module's service, never its repository (ARCHITECTURE.md §2) - only
        # needed for get_document_context() (Sprint 12 Session 16): resolving
        # the linked invoice's billed company and each delivered item's fish
        # name, mirroring InvoiceService's own CompanyService/FishService
        # dependencies exactly.
        self._company_service = CompanyService(session)
        self._fish_service = FishService(session)
        self._company_profile_service = CompanyProfileService(session)

    async def create(
        self,
        payload: DeliveryChallanCreateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> DeliveryChallanResponse:
        await self._validate_invoice_link(payload.invoice_id, tenant_id=tenant_id)

        # challan_number/dispatched_at/delivered_at stay NULL and status is
        # always DRAFT - none is client-supplied (see
        # DeliveryChallanCreateRequest); the number and timestamps are
        # assigned by dispatch()/deliver().
        delivery_challan = DeliveryChallan(
            tenant_id=tenant_id,
            invoice_id=payload.invoice_id,
            challan_number=None,
            challan_date=payload.challan_date,
            status=DeliveryChallanStatus.DRAFT,
            remarks=payload.remarks,
            dispatched_at=None,
            delivered_at=None,
            created_by=actor_id,
            updated_by=actor_id,
        )
        await self._repo.add(delivery_challan)
        await self._commit_or_raise()
        await self._session.refresh(delivery_challan)
        return self._to_response(delivery_challan)

    async def get(
        self, delivery_challan_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> DeliveryChallanResponse:
        delivery_challan = await self._get_or_raise(delivery_challan_id, tenant_id)
        return self._to_response(delivery_challan)

    async def list_delivery_challans(
        self, *, tenant_id: uuid.UUID, params: DeliveryChallanListParams
    ) -> PaginatedResponse[DeliveryChallanResponse]:
        delivery_challans, total = await self._repo.search(
            tenant_id,
            q=params.q,
            status=params.status,
            invoice_id=params.invoice_id,
            challan_date_from=params.challan_date_from,
            challan_date_to=params.challan_date_to,
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
            data=[self._to_response(challan) for challan in delivery_challans], meta=meta
        )

    async def update(
        self,
        delivery_challan_id: uuid.UUID,
        payload: DeliveryChallanUpdateRequest,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> DeliveryChallanResponse:
        delivery_challan = await self._get_or_raise(delivery_challan_id, tenant_id)
        self._ensure_draft(delivery_challan)
        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(delivery_challan, field, value)
        delivery_challan.updated_by = actor_id
        await self._commit_or_raise()
        await self._session.refresh(delivery_challan)
        return self._to_response(delivery_challan)

    async def delete(
        self, delivery_challan_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        delivery_challan = await self._get_or_raise(delivery_challan_id, tenant_id)
        self._ensure_draft(delivery_challan)
        delivery_challan.deleted_at = datetime.now(UTC)
        delivery_challan.deleted_by = actor_id
        await self._session.commit()

    async def add_item(
        self,
        delivery_challan_id: uuid.UUID,
        payload: DeliveryChallanItemCreateRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> DeliveryChallanItemResponse:
        delivery_challan = await self._get_or_raise(delivery_challan_id, tenant_id)
        self._ensure_draft(delivery_challan)
        invoice_item = await self._validate_invoice_item_link(
            delivery_challan,
            payload.invoice_item_id,
            payload.quantity,
            tenant_id,
            exclude_item_id=None,
        )
        line_number = await self._repo.allocate_next_line_number(delivery_challan_id, tenant_id)

        item = DeliveryChallanItem(
            tenant_id=tenant_id,
            delivery_challan_id=delivery_challan_id,
            invoice_item_id=payload.invoice_item_id,
            line_number=line_number,
            quantity=payload.quantity,
            unit=invoice_item.unit,
        )
        await self._repo.add_item(item)
        await self._commit_or_raise()
        await self._session.refresh(item)
        return self._to_item_response(item)

    async def list_items(
        self, delivery_challan_id: uuid.UUID, *, tenant_id: uuid.UUID, sort: str
    ) -> list[DeliveryChallanItemResponse]:
        # Listing is allowed regardless of challan status - only add/edit/
        # delete are restricted to DRAFT.
        await self._get_or_raise(delivery_challan_id, tenant_id)
        items = await self._repo.search_items(delivery_challan_id, tenant_id, sort=sort)
        return [self._to_item_response(item) for item in items]

    async def update_item(
        self,
        delivery_challan_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: DeliveryChallanItemUpdateRequest,
        *,
        tenant_id: uuid.UUID,
    ) -> DeliveryChallanItemResponse:
        delivery_challan = await self._get_or_raise(delivery_challan_id, tenant_id)
        self._ensure_draft(delivery_challan)
        item = await self._get_item_or_raise(delivery_challan_id, item_id, tenant_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "quantity" in update_data:
            await self._validate_invoice_item_link(
                delivery_challan,
                item.invoice_item_id,
                update_data["quantity"],
                tenant_id,
                exclude_item_id=item.id,
            )
            item.quantity = update_data["quantity"]
        await self._commit_or_raise()
        await self._session.refresh(item)
        return self._to_item_response(item)

    async def delete_item(
        self, delivery_challan_id: uuid.UUID, item_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> None:
        delivery_challan = await self._get_or_raise(delivery_challan_id, tenant_id)
        self._ensure_draft(delivery_challan)
        item = await self._get_item_or_raise(delivery_challan_id, item_id, tenant_id)
        await self._repo.delete_item(item)
        await self._commit_or_raise()

    async def get_document_context(
        self, delivery_challan_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> DeliveryChallanDocumentContext:
        """Bundles the delivery challan, its items, its linked invoice, that
        invoice's own items (for each line's description/invoiced quantity),
        each referenced fish's name, the quantity previously delivered
        against each item, the billed company, and the tenant's display
        name for GET /{id}/document (Sprint 12 Session 16) - mirrors
        PurchaseOrderService.get_document_context exactly.

        A delivery challan only has a challan_number once dispatched (the
        transition where this document stops being a mutable draft and
        becomes a real, physical event, mirroring PurchaseOrder's own
        confirm()) - one still DRAFT, or cancelled directly from DRAFT, has
        nothing to print (DeliveryChallanDocumentNotAvailableError, 422). A
        DISPATCHED, DELIVERED, or dispatched-then-CANCELLED challan keeps
        its number and can always be downloaded - the same "gate on the
        number, not the status" rule PurchaseOrderService's own
        get_document_context established, applied here identically.
        """
        delivery_challan = await self._get_or_raise(delivery_challan_id, tenant_id)
        if delivery_challan.challan_number is None:
            raise DeliveryChallanDocumentNotAvailableError(
                "The delivery challan must be dispatched before its document can be generated"
            )

        items = await self._repo.search_items(delivery_challan.id, tenant_id, sort="line_number")

        invoice = await self._invoice_service.get(delivery_challan.invoice_id, tenant_id=tenant_id)

        try:
            company = await self._company_service.get(invoice.company_id, tenant_id=tenant_id)
        except CompanyNotFoundError as exc:
            raise DeliveryChallanCompanyNotFoundError(
                "The specified company does not exist"
            ) from exc

        invoice_items = await self._invoice_service.list_items(
            invoice.id, tenant_id=tenant_id, q=None
        )
        invoice_items_by_id = {invoice_item.id: invoice_item for invoice_item in invoice_items}

        fish_by_id: dict[uuid.UUID, FishResponse] = {}
        for item in items:
            invoice_item = invoice_items_by_id.get(item.invoice_item_id)
            if invoice_item is None or invoice_item.fish_id in fish_by_id:
                continue
            try:
                fish_by_id[invoice_item.fish_id] = await self._fish_service.get(
                    invoice_item.fish_id, tenant_id=tenant_id
                )
            except FishNotFoundError as exc:
                raise DeliveryChallanFishNotFoundError("The specified fish does not exist") from exc

        # Batched, not one query per line (DeliveryChallanRepository.
        # sum_delivered_by_invoice_items) - the same aggregation
        # _validate_invoice_item_link's own over-delivery check uses,
        # reused here rather than re-derived. It already includes this
        # item's own contribution (this challan is DISPATCHED/DELIVERED,
        # both counted), so subtracting the item's own quantity back out
        # gives "delivered by every OTHER line" - a presentational
        # subtraction, not a new business rule.
        invoice_item_ids = list({item.invoice_item_id for item in items})
        delivered_by_invoice_item_id = await self._repo.sum_delivered_by_invoice_items(
            invoice_item_ids, tenant_id
        )
        previously_delivered_by_item_id = {
            item.id: delivered_by_invoice_item_id.get(item.invoice_item_id, Decimal("0"))
            - item.quantity
            for item in items
        }

        tenant_name = await self._get_tenant_name(tenant_id)
        profile_context = await self._company_profile_service.get_document_context(tenant_id)

        return DeliveryChallanDocumentContext(
            delivery_challan=self._to_response(delivery_challan),
            items=[self._to_item_response(item) for item in items],
            invoice=invoice,
            invoice_items_by_id=invoice_items_by_id,
            fish_by_id=fish_by_id,
            previously_delivered_by_item_id=previously_delivered_by_item_id,
            company=company,
            tenant_name=profile_context.display_name or tenant_name,
            tenant_details=profile_context.tenant_details,
            tenant_logo_bytes=profile_context.logo_bytes,
        )

    async def _get_tenant_name(self, tenant_id: uuid.UUID) -> str:
        result = await self._session.execute(select(Tenant.name).where(Tenant.id == tenant_id))
        return result.scalar_one()

    async def dispatch(
        self, delivery_challan_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DeliveryChallanResponse:
        """draft -> dispatched: assigns challan_number and stamps
        dispatched_at, all inside one transaction. Mirrors
        PurchaseOrderService.confirm's shape exactly, minus any totals
        recalculation - there are none. Requires at least one item
        (DeliveryChallanEmptyError) - dispatching an empty challan carries
        nothing to deliver."""
        try:
            delivery_challan = await self._repo.get_by_id_for_update(delivery_challan_id, tenant_id)
            if delivery_challan is None:
                raise DeliveryChallanNotFoundError("Delivery challan not found")
            if delivery_challan.status != DeliveryChallanStatus.DRAFT:
                raise DeliveryChallanInvalidTransitionError(
                    "Only draft delivery challans can be dispatched"
                )

            items = await self._repo.search_items(
                delivery_challan.id, tenant_id, sort="line_number"
            )
            if not items:
                raise DeliveryChallanEmptyError(
                    "A delivery challan must have at least one item to be dispatched"
                )

            delivery_challan.challan_number = await self._allocate_challan_number(
                delivery_challan, tenant_id
            )
            delivery_challan.status = DeliveryChallanStatus.DISPATCHED
            delivery_challan.dispatched_at = datetime.now(UTC)
            delivery_challan.updated_by = actor_id
        except Exception:
            await self._session.rollback()
            raise

        await self._commit_or_raise()
        await self._session.refresh(delivery_challan)
        return self._to_response(delivery_challan)

    async def deliver(
        self, delivery_challan_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DeliveryChallanResponse:
        """dispatched -> delivered (terminal). No side effects on any other
        module - delivery completion never touches supplier/customer
        financials, ledger, or invoice state."""
        delivery_challan = await self._repo.get_by_id_for_update(delivery_challan_id, tenant_id)
        if delivery_challan is None:
            raise DeliveryChallanNotFoundError("Delivery challan not found")
        if delivery_challan.status != DeliveryChallanStatus.DISPATCHED:
            raise DeliveryChallanInvalidTransitionError(
                "Only dispatched delivery challans can be delivered"
            )
        delivery_challan.status = DeliveryChallanStatus.DELIVERED
        delivery_challan.delivered_at = datetime.now(UTC)
        delivery_challan.updated_by = actor_id
        await self._session.commit()
        await self._session.refresh(delivery_challan)
        return self._to_response(delivery_challan)

    async def cancel(
        self, delivery_challan_id: uuid.UUID, *, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DeliveryChallanResponse:
        """draft|dispatched -> cancelled. No side effects on any other
        module - a cancelled delivery challan never affected any
        financial figure, so there is nothing to reverse. Excluded from the
        delivered-quantity aggregation (DeliveryChallanRepository.
        sum_delivered_by_invoice_items), so cancelling immediately frees its
        reserved quantity back up for other challans against the same
        invoice item."""
        delivery_challan = await self._repo.get_by_id_for_update(delivery_challan_id, tenant_id)
        if delivery_challan is None:
            raise DeliveryChallanNotFoundError("Delivery challan not found")
        if delivery_challan.status not in (
            DeliveryChallanStatus.DRAFT,
            DeliveryChallanStatus.DISPATCHED,
        ):
            raise DeliveryChallanInvalidTransitionError(
                "Only draft or dispatched delivery challans can be cancelled"
            )
        delivery_challan.status = DeliveryChallanStatus.CANCELLED
        delivery_challan.updated_by = actor_id
        await self._session.commit()
        await self._session.refresh(delivery_challan)
        return self._to_response(delivery_challan)

    async def _allocate_challan_number(
        self, delivery_challan: DeliveryChallan, tenant_id: uuid.UUID
    ) -> str:
        """Concurrency-safe sequential number allocation: `INSERT ... ON
        CONFLICT DO NOTHING` guarantees the per-tenant/prefix/fiscal-year
        counter row exists without racing a concurrent first allocation for
        that fiscal year, then `SELECT ... FOR UPDATE` locks it so the
        increment below can never be lost to a concurrent dispatch. Only
        called from dispatch(), already inside its transaction. Mirrors
        PurchaseOrderService._allocate_purchase_order_number exactly."""
        fiscal_year = fiscal_year_for(delivery_challan.challan_date)
        await self._repo.ensure_sequence_row(tenant_id, DELIVERY_CHALLAN_NUMBER_PREFIX, fiscal_year)
        sequence = await self._repo.get_sequence_for_update(
            tenant_id, DELIVERY_CHALLAN_NUMBER_PREFIX, fiscal_year
        )
        sequence.last_number += 1
        return format_delivery_challan_number(
            DELIVERY_CHALLAN_NUMBER_PREFIX, fiscal_year, sequence.last_number
        )

    async def _validate_invoice_link(
        self, invoice_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> InvoiceResponse:
        """Enforces the header-level linkage rule: the invoice must exist
        for this tenant (InvoiceService.get() is already tenant-scoped, so a
        foreign-tenant invoice surfaces as "not found" here too) and must be
        ISSUED, PARTIALLY_PAID, or PAID - a DRAFT invoice has no real
        customer commitment to deliver against yet, and a CANCELLED one
        never should. Read-only - never touches Invoice.balance_amount/
        paid_amount or any other Invoice field, mirroring
        PurchaseService._validate_purchase_order_link's own posture toward
        PurchaseOrderService."""
        try:
            invoice = await self._invoice_service.get(invoice_id, tenant_id=tenant_id)
        except InvoiceNotFoundError as exc:
            raise DeliveryChallanInvoiceNotFoundError(
                "The specified invoice does not exist"
            ) from exc
        if invoice.status not in _DELIVERABLE_INVOICE_STATUSES:
            raise DeliveryChallanInvoiceNotDeliverableError(
                "Only issued, partially paid, or paid invoices can be linked to a delivery challan"
            )
        return invoice

    async def _validate_invoice_item_link(
        self,
        delivery_challan: DeliveryChallan,
        invoice_item_id: uuid.UUID,
        quantity: Decimal,
        tenant_id: uuid.UUID,
        *,
        exclude_item_id: uuid.UUID | None,
    ) -> InvoiceItemResponse:
        """The one hard-enforced constraint of this module (Phase 7): a
        challan item's quantity, added to every other challan item already
        delivered against the same invoice item, must never exceed that
        item's own invoiced quantity.

        Runs at add_item/update_item time - while the challan is still
        DRAFT, never deferred to dispatch() - and deliberately counts
        "already delivered" across every valid (non-deleted-challan,
        non-CANCELLED-challan) challan item referencing that invoice item,
        including OTHER DRAFT challans' items, not only DISPATCHED/DELIVERED
        ones (DeliveryChallanRepository.sum_delivered_quantity_for_invoice_item).
        This is a reservation, mirroring PurchaseService._validate_po_item_link
        exactly: two concurrent drafts against the same invoice item are each
        rejected immediately, at entry time, the moment their combined
        quantity would exceed what's invoiced - and since this is a live
        aggregate query, never a stored counter, deleting/cancelling an
        abandoned draft item immediately frees its reserved quantity back up.

        Re-validates the invoice's own deliverable status here too, not just
        once at header-link time, for the same defensive symmetry
        `_validate_po_item_link` applies (nothing in this codebase can
        currently cancel an issued invoice, but this keeps the two modules'
        validation shape identical rather than silently diverging).
        """
        await self._validate_invoice_link(delivery_challan.invoice_id, tenant_id=tenant_id)

        items = await self._invoice_service.list_items(
            delivery_challan.invoice_id, tenant_id=tenant_id, q=None
        )
        invoice_item = next((item for item in items if item.id == invoice_item_id), None)
        if invoice_item is None:
            raise DeliveryChallanInvoiceItemNotFoundError(
                "The specified invoice item does not belong to this delivery challan's "
                "linked invoice"
            )

        already_delivered = await self._repo.sum_delivered_quantity_for_invoice_item(
            invoice_item_id, tenant_id, exclude_item_id=exclude_item_id
        )
        if already_delivered + quantity > invoice_item.quantity:
            remaining = invoice_item.quantity - already_delivered
            raise DeliveryChallanOverDeliveryError(
                f"Delivery quantity {quantity} exceeds the remaining {remaining} "
                f"{invoice_item.unit} on this invoice item"
            )
        return invoice_item

    @staticmethod
    def _ensure_draft(delivery_challan: DeliveryChallan) -> None:
        if delivery_challan.status != DeliveryChallanStatus.DRAFT:
            raise DeliveryChallanNotDraftError(
                "Only draft delivery challans can be edited, deleted, or mutated"
            )

    async def _get_or_raise(
        self, delivery_challan_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DeliveryChallan:
        delivery_challan = await self._repo.get_by_id(delivery_challan_id, tenant_id)
        if delivery_challan is None:
            raise DeliveryChallanNotFoundError("Delivery challan not found")
        return delivery_challan

    async def _get_item_or_raise(
        self, delivery_challan_id: uuid.UUID, item_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DeliveryChallanItem:
        item = await self._repo.get_item_by_id(item_id, delivery_challan_id, tenant_id)
        if item is None:
            raise DeliveryChallanItemNotFoundError("Delivery challan item not found")
        return item

    async def _commit_or_raise(self) -> None:
        """Commit, translating a unique-constraint violation into a clean
        409 - the same race-avoidance rationale PurchaseOrderService/
        PurchaseService give for their own unique constraints."""
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._translate_integrity_error(exc) from exc

    @staticmethod
    def _translate_integrity_error(exc: IntegrityError) -> AppException:
        driver_error = getattr(exc.orig, "__cause__", None)
        constraint = getattr(driver_error, "constraint_name", None) or ""
        if constraint == "ix_delivery_challans_tenant_challan_number":
            return DeliveryChallanNumberConflictError(
                "This challan number is already in use for this tenant"
            )
        return ConflictError("This operation conflicts with existing data")

    @staticmethod
    def _to_response(delivery_challan: DeliveryChallan) -> DeliveryChallanResponse:
        return DeliveryChallanResponse.model_validate(delivery_challan)

    @staticmethod
    def _to_item_response(item: DeliveryChallanItem) -> DeliveryChallanItemResponse:
        return DeliveryChallanItemResponse.model_validate(item)
