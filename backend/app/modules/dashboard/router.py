from fastapi import APIRouter, Depends

from app.common.schemas import ErrorResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.permissions import DASHBOARD_VIEW
from app.modules.dashboard.schemas import DashboardResponse
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Owner's homepage: one consolidated, read-only business overview",
    description=(
        "Aggregates KPIs, operations, financial, recent activity, alerts and chart "
        "series (monthly sales, monthly purchases, top-10 fish by sales, trip status "
        "distribution) across invoices, payments, trips, boats, trip catches, purchase "
        "bills and supplier payments for the caller's tenant. Entirely computed "
        "server-side via grouped SQL aggregates - no mutation, no per-request business "
        "logic in the client. Reports, ledgers and profitability are out of scope for "
        "this endpoint and land in later sprints."
    ),
    responses={**_COMMON_ERROR_RESPONSES},
    dependencies=[Depends(require_permission(DASHBOARD_VIEW))],
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    return await service.get_dashboard(tenant_id=current_user.tenant_id)
