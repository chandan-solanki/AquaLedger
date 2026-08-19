from fastapi import APIRouter, Depends

from app.common.schemas import ErrorResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission

# Reuses Company Profile's settings:manage permission rather than
# introducing numbering_sequence:view/edit - every role that can see the
# Settings nav group already requires settings:manage (frontend
# navigation.ts gates Company Profile/Numbering Sequences/Categories
# identically, per company_profile/permissions.py's own docstring), so a
# separate permission here would gate nothing an existing role doesn't
# already need.
from app.modules.company_profile.permissions import SETTINGS_MANAGE
from app.modules.numbering_sequences.dependencies import get_numbering_sequence_service
from app.modules.numbering_sequences.schemas import NumberingSequenceResponse
from app.modules.numbering_sequences.service import NumberingSequenceService

router = APIRouter(prefix="/numbering-sequences", tags=["numbering-sequences"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}


@router.get(
    "",
    response_model=list[NumberingSequenceResponse],
    summary="Current numbering status for every business document type",
    description=(
        "Read-only snapshot of the caller's own tenant's document numbering: prefix, "
        "current fiscal year, last issued number and the next number each of the six "
        "independent sequence allocators (invoices, purchase bills, purchase orders, "
        "customer payments, supplier payments, delivery challans) would hand out right "
        "now. Never allocates a number itself, and never another tenant's data."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(SETTINGS_MANAGE))],
)
async def list_numbering_sequences(
    current_user: User = Depends(get_current_user),
    service: NumberingSequenceService = Depends(get_numbering_sequence_service),
) -> list[NumberingSequenceResponse]:
    return await service.list_sequences(tenant_id=current_user.tenant_id)
