import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.common.schemas import ErrorResponse, PaginatedResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.permissions import require_permission
from app.modules.documents.dependencies import get_document_record_service
from app.modules.documents.permissions import DOCUMENT_VIEW
from app.modules.documents.schemas import DocumentListParams, DocumentRecordResponse
from app.modules.documents.service import DocumentRecordService

router = APIRouter(prefix="/documents", tags=["documents"])


def _error_example(code: str, message: str) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": None,
            "field_errors": None,
            "request_id": "e9fefc78-4d47-4788-8d33-427f5b7852c8",
            "timestamp": "2026-08-15T04:00:00Z",
        }
    }


_COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    403: {"model": ErrorResponse, "description": "Missing required permission"},
}

_DOCUMENT_RECORD_EXAMPLE: dict[str, object] = {
    "id": "019f9b1a-2f3e-7c31-9d4a-6b2e5f9a1c07",
    "document_type": "invoice",
    "document_number": "INV/2026-27/00001",
    "party_type": "customer",
    "party_id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
    "party_name": "ABC Sea Food",
    "generated_at": "2026-08-15T04:00:00Z",
    "generated_by": "019f83c8-6489-7bcf-beba-c241b7abbb04",
    "generated_by_name": "Admin",
    "file_name": "Invoice_INV2026-2700001.pdf",
    "file_extension": "pdf",
    "content_type": "application/pdf",
    "file_size": 48213,
}
_LIST_RESPONSE_EXAMPLE: dict[str, object] = {
    "data": [_DOCUMENT_RECORD_EXAMPLE],
    "meta": {
        "total_records": 1,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 20,
        "has_next": False,
        "has_previous": False,
    },
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, object]] = {
    404: {
        "model": ErrorResponse,
        "description": "Document not found",
        "content": {
            "application/json": {
                "examples": {
                    "document_not_found": {
                        "summary": "No DocumentRecord with this id for this tenant",
                        "value": _error_example("DOCUMENT_RECORD_NOT_FOUND", "Document not found"),
                    },
                    "file_missing": {
                        "summary": "The record exists but its file is no longer in storage",
                        "value": _error_example(
                            "DOCUMENT_FILE_MISSING",
                            "The file for this document is no longer available",
                        ),
                    },
                }
            }
        },
    },
}


@router.get(
    "",
    response_model=PaginatedResponse[DocumentRecordResponse],
    summary="Search, filter and paginate the Document Center's generated-document history",
    description=(
        "Every DocumentRecord for the caller's tenant - each row is one generation event "
        "of a business document (Invoice, Purchase Bill, Customer/Supplier Payment "
        "Receipt), not a catalog of every business record that could theoretically have "
        "a document. `q` searches document_number, party_name and file_name "
        "(case-insensitive substring). Combine with document_type/party_type/party_id/"
        "from_date/to_date filters, `sort` (one of `generated_at`, `document_number`; "
        "prefix with `-` for descending, e.g. `-generated_at`) and page/page_size."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        200: {"content": {"application/json": {"example": _LIST_RESPONSE_EXAMPLE}}},
        422: {
            "model": ErrorResponse,
            "description": "Invalid sort field, invalid date range, or page/page_size out of range",
        },
    },
    dependencies=[Depends(require_permission(DOCUMENT_VIEW))],
)
async def list_documents(
    params: Annotated[DocumentListParams, Query()],
    current_user: User = Depends(get_current_user),
    service: DocumentRecordService = Depends(get_document_record_service),
) -> PaginatedResponse[DocumentRecordResponse]:
    return await service.list_documents(tenant_id=current_user.tenant_id, params=params)


@router.get(
    "/{document_id}/download",
    summary="Download a previously generated document by its Document Center record id",
    description=(
        "Streams the file bytes for one DocumentRecord, resolved tenant-scoped and read "
        "through the shared StorageService (app.core.document_engine) - the client "
        "supplies only `document_id`; the physical storage key never leaves the server. "
        "Content-Type and the download filename both come from the record's own stored "
        "metadata, not recomputed here."
    ),
    responses={
        **_COMMON_ERROR_RESPONSES,
        **_NOT_FOUND_RESPONSE,
        200: {
            "description": "The stored file",
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        },
    },
    dependencies=[Depends(require_permission(DOCUMENT_VIEW))],
)
async def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentRecordService = Depends(get_document_record_service),
) -> Response:
    download = await service.download(document_id, tenant_id=current_user.tenant_id)
    return Response(
        content=download.content,
        media_type=download.content_type,
        headers={"Content-Disposition": f'attachment; filename="{download.file_name}"'},
    )
