from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.modules.numbering_sequences.constants import NumberingDocumentType


class NumberingSequenceStatus(StrEnum):
    """Whether this tenant has issued any document under this counter in
    the current fiscal year yet - purely informational, never a switch an
    administrator can flip (this Settings page is read-only, see the
    Sprint 14 Session 2 audit)."""

    ACTIVE = "active"
    NOT_STARTED = "not_started"


class NumberingSequenceResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    document_type: NumberingDocumentType
    document_label: str
    prefix: str
    fiscal_year: str
    current_number: int
    next_number: int
    next_number_formatted: str
    number_format: str
    status: NumberingSequenceStatus
