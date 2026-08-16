from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.documents.service import DocumentRecordService


async def get_document_record_service(
    session: AsyncSession = Depends(get_db),
) -> DocumentRecordService:
    return DocumentRecordService(session)
