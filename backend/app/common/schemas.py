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
