from fastapi import APIRouter

from app.api.v1 import health
from app.modules.auth.router import router as auth_router
from app.modules.boats.router import router as boats_router
from app.modules.companies.router import router as companies_router
from app.modules.fish.router import router as fish_router
from app.modules.invoices.router import router as invoices_router
from app.modules.payments.router import router as payments_router
from app.modules.purchase.router import router as purchase_router
from app.modules.suppliers.router import router as suppliers_router
from app.modules.trip_catches.router import router as trip_catches_router
from app.modules.trip_expenses.router import router as trip_expenses_router
from app.modules.trips.router import router as trips_router

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(fish_router)
api_v1_router.include_router(boats_router)
api_v1_router.include_router(trips_router)
api_v1_router.include_router(trip_catches_router)
api_v1_router.include_router(trip_expenses_router)
api_v1_router.include_router(invoices_router)
api_v1_router.include_router(payments_router)
api_v1_router.include_router(suppliers_router)
api_v1_router.include_router(purchase_router)
