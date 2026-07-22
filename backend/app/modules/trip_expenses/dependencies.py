from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.trip_expenses.service import TripExpenseService


async def get_trip_expense_service(session: AsyncSession = Depends(get_db)) -> TripExpenseService:
    return TripExpenseService(session)
