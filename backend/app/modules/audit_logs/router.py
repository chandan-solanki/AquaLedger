"""Audit Logs - Sprint 14 Session 5.

Read-only, list-only: there is no create/update/delete endpoint and no
GET /audit-logs/{id} detail endpoint. Reasons:

1. AuditLog rows are historical facts (append-only - see the model's own
   docstring: no updated_at). Nothing in this module, or anywhere else,
   should ever mutate one.
2. Every field on an AuditLog row is small (an action code, an entity
   reference, a compact JSONB `changes` diff, request metadata) - there is
   no heavy field worth hiding from the list response and fetching lazily
   on a detail page, unlike e.g. a document's file bytes. The list item
   already carries everything a row has.

This session also does not implement the full ARCHITECTURE.md Sec 37
vision (before_flush auto-diffing every entity, SHA-256 hash chaining,
monthly partitioning, 7-year retention). That is intentionally deferred -
see ARCHITECTURE.md's updated Sec 37 note. What ships here is the minimum
that makes the existing, already-written-but-never-readable audit trail
(auth's login/logout/password-change events, now joined by Users module
create/update/status/role-change events) visible to an administrator, with
tenant-scoped, filtered, paginated search.

Gated on `audit_log:view` - a permission that already existed in the
baseline seed data (67c33121fc54) and already labeled the Administration ->
Audit Logs nav entry (frontend navigation.ts), granted to
super_admin/admin/manager but not accountant/operator. `user:manage` is
deliberately not reused here: the existing architecture already
distinguishes audit access from user administration (manager holds
audit_log:view but not user:manage).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.audit_logs.constants import AUDIT_LOG_VIEW_PERMISSION
from app.modules.audit_logs.dependencies import get_audit_log_service
from app.modules.audit_logs.schemas import AuditLogListItem, AuditLogListParams
from app.modules.audit_logs.service import AuditLogService
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])

_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogListItem],
    summary="Search, filter, sort and paginate audit log entries",
    description=(
        "Every audit record for the caller's tenant, newest first by default. "
        "`q` searches the acting user's full_name, email and username. Combine "
        "with action/entity_type/user_id/from_date/to_date filters, `sort` "
        "(created_at or -created_at) and page/page_size. Read-only: there is no "
        "create, update or delete endpoint - audit records are append-only history."
    ),
    responses=_COMMON_ERROR_RESPONSES,
    dependencies=[Depends(require_permission(AUDIT_LOG_VIEW_PERMISSION))],
)
async def list_audit_logs(
    params: Annotated[AuditLogListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: AuditLogService = Depends(get_audit_log_service),
) -> PaginatedResponse[AuditLogListItem]:
    return await service.list_logs(tenant_id=current_user.tenant_id, params=params)
