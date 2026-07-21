from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    field_errors: dict[str, list[str]] | None = None
    request_id: str | None = None
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationMeta(BaseModel):
    total_records: int
    total_pages: int
    current_page: int
    page_size: int
    has_next: bool
    has_previous: bool


class PaginatedResponse[T](BaseModel):
    data: list[T]
    meta: PaginationMeta
