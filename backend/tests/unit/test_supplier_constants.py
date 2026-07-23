from app.modules.suppliers.constants import SupplierStatus


def test_supplier_status_values() -> None:
    assert set(SupplierStatus) == {SupplierStatus.ACTIVE, SupplierStatus.INACTIVE}
    assert SupplierStatus.ACTIVE.value == "active"
    assert SupplierStatus.INACTIVE.value == "inactive"
