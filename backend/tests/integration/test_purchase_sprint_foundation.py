"""Structural verification for the suppliers/purchase modules (TASKS.md's
testing checklist: "Swagger loads", "Routers registered", "Models load",
"Relationships resolve", "No mapper errors"). Originally written in Sprint
11 Session 1 when both routers carried zero endpoints; updated in Session 2
now that Supplier/Purchase Bill CRUD is registered - see test_supplier_api.py
/test_purchase_api.py for the endpoint-level coverage.
"""

from sqlalchemy.orm import configure_mappers

from app.api.v1.router import api_v1_router
from app.main import app
from app.modules.purchase.router import router as purchase_router
from app.modules.suppliers.router import router as suppliers_router


def test_mappers_configure_without_error() -> None:
    """Fails loudly if any relationship (Supplier<->PurchaseBill,
    PurchaseBill<->PurchaseBillItem) references a typo'd class name or a
    back_populates that doesn't exist on the other side."""
    configure_mappers()


def test_openapi_schema_builds_without_error() -> None:
    schema = app.openapi()
    assert schema["info"]["title"]


class TestRouterRegistration:
    def test_suppliers_router_has_the_expected_prefix(self) -> None:
        assert suppliers_router.prefix == "/suppliers"

    def test_purchase_router_has_the_expected_prefix(self) -> None:
        assert purchase_router.prefix == "/purchase"

    def test_suppliers_and_purchase_routers_included_in_api_v1(self) -> None:
        # FastAPI wraps each include_router() call in a lazy _IncludedRouter
        # holding the original sub-router - checking object identity here is
        # more robust than string-matching a path format across FastAPI
        # internals.
        included_originals = [getattr(r, "original_router", None) for r in api_v1_router.routes]
        assert suppliers_router in included_originals
        assert purchase_router in included_originals

    def test_both_routers_now_carry_crud_endpoints(self) -> None:
        # Suppliers: 5 CRUD endpoints (create/list/get/update/delete), still
        # unchanged since Session 2. Purchase: those same 5 plus Session 3's
        # 4 item endpoints (add/list/update/delete) plus Session 5's single
        # post endpoint.
        assert len(suppliers_router.routes) == 5
        assert len(purchase_router.routes) == 10
