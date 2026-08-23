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
        """Explicit (method, path) checks (Sprint 17 Session 7), not a raw
        route count. A count assertion breaks the moment any legitimate,
        unrelated endpoint is added - e.g. `GET .../document` (PDF
        generation, added on the purchase router after this test was last
        updated) silently pushed the real total from 10 to 11 with no
        indication of what actually changed. Checking for these specific
        required (method, path) pairs instead fails clearly and
        specifically if a real CRUD endpoint is ever removed, while
        tolerating any future endpoint (document generation, posting,
        etc.) this test isn't about.
        """
        suppliers_routes = {
            (method, route.path) for route in suppliers_router.routes for method in route.methods
        }
        purchase_routes = {
            (method, route.path) for route in purchase_router.routes for method in route.methods
        }

        required_supplier_routes = {
            ("POST", "/suppliers"),
            ("GET", "/suppliers"),
            ("GET", "/suppliers/{supplier_id}"),
            ("PUT", "/suppliers/{supplier_id}"),
            ("DELETE", "/suppliers/{supplier_id}"),
        }
        # Purchase's 5 bill-level CRUD endpoints (create/list/get/update/
        # delete, unchanged since Session 2), plus Session 3's 4 item
        # endpoints (add/list/update/delete), plus Session 5's post
        # endpoint - 10 required routes. `GET .../document` is a real,
        # separately-tested 11th endpoint (PDF generation), deliberately
        # not part of this CRUD-contract checklist.
        required_purchase_routes = {
            ("POST", "/purchase"),
            ("GET", "/purchase"),
            ("GET", "/purchase/{purchase_bill_id}"),
            ("PUT", "/purchase/{purchase_bill_id}"),
            ("DELETE", "/purchase/{purchase_bill_id}"),
            ("POST", "/purchase/{purchase_bill_id}/items"),
            ("GET", "/purchase/{purchase_bill_id}/items"),
            ("PUT", "/purchase/{purchase_bill_id}/items/{item_id}"),
            ("DELETE", "/purchase/{purchase_bill_id}/items/{item_id}"),
            ("POST", "/purchase/{purchase_bill_id}/post"),
        }

        assert required_supplier_routes.issubset(suppliers_routes)
        assert required_purchase_routes.issubset(purchase_routes)
