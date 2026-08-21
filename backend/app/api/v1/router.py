from fastapi import APIRouter

from app.api.v1 import health
from app.modules.audit_logs.router import router as audit_logs_router
from app.modules.auth.router import router as auth_router
from app.modules.boats.router import router as boats_router
from app.modules.companies.router import router as companies_router
from app.modules.company_profile.router import router as company_profile_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.delivery_challans.router import router as delivery_challans_router
from app.modules.documents.router import router as documents_router
from app.modules.fish.router import router as fish_router
from app.modules.invoices.router import router as invoices_router
from app.modules.numbering_sequences.router import router as numbering_sequences_router
from app.modules.payments.router import router as payments_router
from app.modules.purchase.router import router as purchase_router
from app.modules.purchase_orders.router import router as purchase_orders_router
from app.modules.reports.router import router as reports_router
from app.modules.roles.router import router as roles_router
from app.modules.supplier_payments.router import router as supplier_payments_router
from app.modules.suppliers.router import router as suppliers_router
from app.modules.trip_catches.router import fish_stock_router
from app.modules.trip_catches.router import router as trip_catches_router
from app.modules.trip_expenses.router import router as trip_expenses_router
from app.modules.trips.router import router as trips_router
from app.modules.users.router import router as users_router

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(company_profile_router)
api_v1_router.include_router(fish_router)
api_v1_router.include_router(boats_router)
api_v1_router.include_router(trips_router)
api_v1_router.include_router(trip_catches_router)
api_v1_router.include_router(fish_stock_router)
api_v1_router.include_router(trip_expenses_router)
api_v1_router.include_router(invoices_router)
api_v1_router.include_router(payments_router)
api_v1_router.include_router(delivery_challans_router)
api_v1_router.include_router(suppliers_router)
api_v1_router.include_router(purchase_router)
api_v1_router.include_router(purchase_orders_router)
api_v1_router.include_router(supplier_payments_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(numbering_sequences_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(roles_router)
api_v1_router.include_router(audit_logs_router)
