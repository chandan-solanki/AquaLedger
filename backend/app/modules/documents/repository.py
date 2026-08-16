import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.documents.constants import PartyType
from app.modules.documents.models import DocumentRecord

_SORT_COLUMNS: dict[str, Any] = {
    "generated_at": DocumentRecord.generated_at,
    "document_number": DocumentRecord.document_number,
}


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


class DocumentRecordRepository:
    """All raw queries for the documents (Document Center) module live
    here - services never build SQL (ARCHITECTURE.md §3.2)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: DocumentRecord) -> DocumentRecord:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits as a single, deliberate
        step."""
        self._session.add(record)
        return record

    async def get_by_id(
        self, document_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DocumentRecord | None:
        result = await self._session.execute(
            select(DocumentRecord)
            .options(selectinload(DocumentRecord.generated_by_user))
            .where(DocumentRecord.id == document_id, DocumentRecord.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        document_type: str | None,
        party_type: PartyType | None,
        party_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[DocumentRecord], int]:
        """Filtered, sorted, paginated document history plus the total
        match count. Two queries (count + page), not N+1. `generated_by_user`
        is eager-loaded (selectinload - one extra query total, not one per
        row) so the service can read `generated_by_name` without a
        per-row lookup. Tie-broken by id in the same direction as the
        primary sort, mirroring every other module's search()."""
        conditions = [DocumentRecord.tenant_id == tenant_id]
        if document_type is not None:
            conditions.append(DocumentRecord.document_type == document_type)
        if party_type is not None:
            conditions.append(DocumentRecord.party_type == party_type.value)
        if party_id is not None:
            conditions.append(DocumentRecord.party_id == party_id)
        if from_date is not None:
            conditions.append(DocumentRecord.generated_at >= _day_start(from_date))
        if to_date is not None:
            conditions.append(DocumentRecord.generated_at < _day_start(to_date + timedelta(days=1)))
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    DocumentRecord.document_number.ilike(pattern),
                    DocumentRecord.party_name.ilike(pattern),
                    DocumentRecord.file_name.ilike(pattern),
                )
            )

        total = (
            await self._session.execute(
                select(func.count()).select_from(DocumentRecord).where(*conditions)
            )
        ).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        descending = sort.startswith("-")
        order = column.desc() if descending else column.asc()
        tie_break = DocumentRecord.id.desc() if descending else DocumentRecord.id.asc()

        rows = (
            (
                await self._session.execute(
                    select(DocumentRecord)
                    .options(selectinload(DocumentRecord.generated_by_user))
                    .where(*conditions)
                    .order_by(order, tie_break)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total
