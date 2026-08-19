import math
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginatedResponse, PaginationMeta
from app.modules.audit_logs.repository import AuditLogRepository
from app.modules.audit_logs.schemas import AuditLogActor, AuditLogListItem, AuditLogListParams
from app.modules.auth.models import AuditLog


class AuditLogService:
    """Read-only by design - audit records are historical facts (AuditLog
    has no updated_at; see its docstring). There is no create/update/delete
    method here: every write already goes through
    AuthRepository.add_audit_log from the module performing the action
    (auth, users), not from this one.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditLogRepository(session)

    async def list_logs(
        self, *, tenant_id: uuid.UUID, params: AuditLogListParams
    ) -> PaginatedResponse[AuditLogListItem]:
        rows, total = await self._repo.search(
            tenant_id,
            q=params.q,
            action=params.action,
            entity_type=params.entity_type,
            user_id=params.user_id,
            from_date=params.from_date,
            to_date=params.to_date,
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
        return PaginatedResponse(data=[self._to_list_item(row) for row in rows], meta=meta)

    @staticmethod
    def _to_list_item(log: AuditLog) -> AuditLogListItem:
        actor = (
            AuditLogActor(id=log.user.id, full_name=log.user.full_name, email=log.user.email)
            if log.user is not None
            else None
        )
        return AuditLogListItem(
            id=log.id,
            tenant_id=log.tenant_id,
            actor=actor,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            changes=log.changes,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at,
        )
