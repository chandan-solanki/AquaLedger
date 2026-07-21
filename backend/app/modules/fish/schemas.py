import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.fish.constants import FishUnit

# HSN codes are numeric, 4/6/8 digits per GST convention.
_HSN_RE = re.compile(r"^[0-9]{4,8}$")


def _validate_hsn_code(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not _HSN_RE.match(value):
        raise ValueError("HSN code must be 4, 6 or 8 digits")
    return value


class FishResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "019f83c8-6489-7bcf-beba-c241b7abbb03",
                "tenant_id": "019f7af3-83ae-783a-b139-40a239786b2f",
                "code": "FISH-001",
                "name": "Pomfret",
                "local_name": "Paplet",
                "scientific_name": "Pampus argenteus",
                "category": "Whitefish",
                "unit": "kg",
                "default_purchase_rate": "450.0000",
                "default_sale_rate": "550.0000",
                "hsn_code": "0302",
                "description": None,
                "is_active": True,
                "created_at": "2026-07-21T09:48:08.714017Z",
                "updated_at": "2026-07-21T09:48:08.714017Z",
            }
        },
    )

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    local_name: str | None
    scientific_name: str | None
    category: str | None
    unit: FishUnit
    default_purchase_rate: Decimal | None
    default_sale_rate: Decimal | None
    hsn_code: str | None
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FishCreateRequest(BaseModel):
    """tenant_id, created_by and updated_by are never client-supplied - the
    router populates them from the authenticated user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "FISH-001",
                "name": "Pomfret",
                "local_name": "Paplet",
                "scientific_name": "Pampus argenteus",
                "category": "Whitefish",
                "unit": "kg",
                "default_purchase_rate": "450.0000",
                "default_sale_rate": "550.0000",
                "hsn_code": "0302",
            }
        }
    )

    code: str = Field(
        min_length=1, max_length=50, examples=["FISH-001"], description="Unique per tenant."
    )
    name: str = Field(
        min_length=1,
        max_length=255,
        examples=["Pomfret"],
        description="Unique per tenant, case-insensitive.",
    )
    local_name: str | None = Field(default=None, max_length=255, examples=["Paplet"])
    scientific_name: str | None = Field(default=None, max_length=255, examples=["Pampus argenteus"])
    category: str | None = Field(default=None, max_length=100, examples=["Whitefish"])
    unit: FishUnit = Field(default=FishUnit.KG, description="Unit fish is traded in.")
    default_purchase_rate: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=4, examples=["450.0000"]
    )
    default_sale_rate: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=4, examples=["550.0000"]
    )
    hsn_code: str | None = Field(
        default=None,
        max_length=20,
        examples=["0302"],
        description="GST HSN/SAC code - 4, 6 or 8 digits.",
    )
    description: str | None = None
    is_active: bool = True

    _check_hsn_code = field_validator("hsn_code")(_validate_hsn_code)


class FishUpdateRequest(BaseModel):
    """Partial update - only fields present in the request body are changed."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "default_purchase_rate": "460.0000",
                "default_sale_rate": "560.0000",
            }
        }
    )

    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    local_name: str | None = Field(default=None, max_length=255)
    scientific_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: FishUnit | None = None
    default_purchase_rate: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=4
    )
    default_sale_rate: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    hsn_code: str | None = Field(default=None, max_length=20)
    description: str | None = None
    is_active: bool | None = None

    _check_hsn_code = field_validator("hsn_code")(_validate_hsn_code)


_SORTABLE_FIELDS = frozenset({"name", "code", "created_at", "updated_at"})


class FishListParams(BaseModel):
    """Query params for GET /fish - bound via FastAPI's Depends() model support."""

    q: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive search across code, name, local_name and scientific_name.",
        examples=["pomfret"],
    )
    category: str | None = Field(default=None, max_length=100, examples=["Whitefish"])
    unit: FishUnit | None = Field(default=None, examples=[FishUnit.KG])
    is_active: bool | None = Field(default=None, examples=[True])
    sort: str = Field(
        default="-created_at",
        description="One of name, code, created_at, updated_at; prefix with '-' for descending.",
        examples=["name", "-created_at"],
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("sort")
    @classmethod
    def _check_sort(cls, value: str) -> str:
        field = value[1:] if value.startswith("-") else value
        if field not in _SORTABLE_FIELDS:
            raise ValueError(
                f"Invalid sort field '{field}'. Allowed: {', '.join(sorted(_SORTABLE_FIELDS))}"
            )
        return value
