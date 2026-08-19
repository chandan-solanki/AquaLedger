import datetime as dt
import uuid
from dataclasses import dataclass

from app.modules.numbering_sequences.constants import NumberingDocumentType
from app.modules.numbering_sequences.schemas import NumberingSequenceStatus
from app.modules.numbering_sequences.service import NumberingSequenceService

_TENANT_ID = uuid.uuid4()


@dataclass(frozen=True)
class _Row:
    last_number: int


class _FakeRepo:
    """Stands in for NumberingSequenceRepository - every getter defaults to
    "no row yet" so a test only has to override the one sequence it cares
    about, mirroring test_dashboard_service.py's _FakeDashboardRepo."""

    def __init__(self, **overrides: int) -> None:
        self._overrides = overrides

    async def _get(self, key: str) -> _Row | None:
        if key not in self._overrides:
            return None
        return _Row(last_number=self._overrides[key])

    async def get_invoice_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> _Row | None:
        return await self._get("invoice")

    async def get_purchase_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> _Row | None:
        return await self._get("purchase_bill")

    async def get_purchase_order_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> _Row | None:
        return await self._get("purchase_order")

    async def get_payment_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> _Row | None:
        return await self._get("customer_payment")

    async def get_supplier_payment_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> _Row | None:
        return await self._get("supplier_payment")

    async def get_delivery_challan_sequence(
        self, tenant_id: uuid.UUID, prefix: str, fiscal_year: str
    ) -> _Row | None:
        return await self._get("delivery_challan")


def _service(**overrides: int) -> NumberingSequenceService:
    service = NumberingSequenceService.__new__(NumberingSequenceService)
    service._repo = _FakeRepo(**overrides)  # type: ignore[assignment]
    return service


class TestListSequences:
    async def test_returns_all_six_document_types(self) -> None:
        results = await _service().list_sequences(_TENANT_ID, today=dt.date(2026, 7, 22))
        assert [item.document_type for item in results] == list(NumberingDocumentType)

    async def test_unused_sequence_is_not_started_with_next_number_one(self) -> None:
        results = await _service().list_sequences(_TENANT_ID, today=dt.date(2026, 7, 22))
        invoice = next(r for r in results if r.document_type == NumberingDocumentType.INVOICE)
        assert invoice.current_number == 0
        assert invoice.next_number == 1
        assert invoice.status == NumberingSequenceStatus.NOT_STARTED
        assert invoice.prefix == "INV"
        assert invoice.document_label == "Invoice"

    async def test_used_sequence_reflects_last_number_and_is_active(self) -> None:
        results = await _service(invoice=41).list_sequences(_TENANT_ID, today=dt.date(2026, 7, 22))
        invoice = next(r for r in results if r.document_type == NumberingDocumentType.INVOICE)
        assert invoice.current_number == 41
        assert invoice.next_number == 42
        assert invoice.next_number_formatted == "INV/2026-27/00042"
        assert invoice.status == NumberingSequenceStatus.ACTIVE

    async def test_fiscal_year_boundary_april_1(self) -> None:
        before = await _service().list_sequences(_TENANT_ID, today=dt.date(2026, 3, 31))
        after = await _service().list_sequences(_TENANT_ID, today=dt.date(2026, 4, 1))
        assert before[0].fiscal_year == "2025-26"
        assert after[0].fiscal_year == "2026-27"

    async def test_each_document_type_uses_its_own_prefix(self) -> None:
        results = await _service(
            purchase_bill=1,
            purchase_order=2,
            customer_payment=3,
            supplier_payment=4,
            delivery_challan=5,
        ).list_sequences(_TENANT_ID, today=dt.date(2026, 7, 22))
        by_type = {item.document_type: item for item in results}
        assert by_type[NumberingDocumentType.PURCHASE_BILL].prefix == "PUR"
        assert by_type[NumberingDocumentType.PURCHASE_ORDER].prefix == "PO"
        assert by_type[NumberingDocumentType.CUSTOMER_PAYMENT].prefix == "PAY"
        assert by_type[NumberingDocumentType.SUPPLIER_PAYMENT].prefix == "SPAY"
        assert by_type[NumberingDocumentType.DELIVERY_CHALLAN].prefix == "DC"
