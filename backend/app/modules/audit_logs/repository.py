import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import AuditLog, User

_SORT_COLUMNS: dict[str, Any] = {"created_at": AuditLog.created_at}


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


class AuditLogRepository:
    """All raw queries for the audit-logs module live here - services never
    build SQL. Read-only: there is no write method here on purpose. Every
    write path already exists on AuthRepository.add_audit_log (auth,
    users); audit_logs is append-only history owned by no single module's
    CRUD, so this repository only ever reads it.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        q: str | None,
        action: str | None,
        entity_type: str | None,
        user_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[AuditLog], int]:
        """Filtered, sorted, paginated audit log list plus the total match
        count. Two queries (count + page), tie-broken by id for stable
        pagination - mirrors UserRepository.search / DocumentRecordRepository.
        """
        conditions = [AuditLog.tenant_id == tenant_id]
        if action is not None:
            conditions.append(AuditLog.action == action)
        if entity_type is not None:
            conditions.append(AuditLog.entity_type == entity_type)
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)
        if from_date is not None:
            conditions.append(AuditLog.created_at >= _day_start(from_date))
        if to_date is not None:
            conditions.append(AuditLog.created_at < _day_start(to_date + timedelta(days=1)))

        count_stmt = select(func.count()).select_from(AuditLog).where(*conditions)
        row_stmt = select(AuditLog).where(*conditions).options(selectinload(AuditLog.user))

        if q and q.strip():
            pattern = f"%{q.strip()}%"
            search_clause = or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            )
            count_stmt = (
                select(func.count(func.distinct(AuditLog.id)))
                .select_from(AuditLog)
                .join(User, User.id == AuditLog.user_id)
                .where(*conditions, search_clause)
            )
            row_stmt = (
                select(AuditLog)
                .join(User, User.id == AuditLog.user_id)
                .where(*conditions, search_clause)
                .options(selectinload(AuditLog.user))
            )

        total = (await self._session.execute(count_stmt)).scalar_one()

        sort_field = sort[1:] if sort.startswith("-") else sort
        column = _SORT_COLUMNS[sort_field]
        order = column.desc() if sort.startswith("-") else column.asc()

        rows = (
            (
                await self._session.execute(
                    row_stmt.order_by(order, AuditLog.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total
