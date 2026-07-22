from fastapi import APIRouter

from app.api.v1 import health
from app.modules.auth.router import router as auth_router
from app.modules.boats.router import router as boats_router
from app.modules.companies.router import router as companies_router
from app.modules.fish.router import router as fish_router
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
