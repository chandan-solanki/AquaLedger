from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.numbering_sequences.service import NumberingSequenceService


async def get_numbering_sequence_service(
    session: AsyncSession = Depends(get_db),
) -> NumberingSequenceService:
    return NumberingSequenceService(session)
