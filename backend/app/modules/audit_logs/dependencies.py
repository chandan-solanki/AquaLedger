from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.audit_logs.service import AuditLogService


async def get_audit_log_service(session: AsyncSession = Depends(get_db)) -> AuditLogService:
    return AuditLogService(session)
