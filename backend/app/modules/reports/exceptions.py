from app.core.errors import NotFoundError


class ReportCustomerNotFoundError(NotFoundError):
    """Raised when a Customer Ledger request's `customer_id` doesn't
    reference an existing company for the caller's tenant - also covers a
    company belonging to another tenant, which is indistinguishable from
    "does not exist" by design (mirrors InvoiceCompanyNotFoundError)."""

    code = "REPORT_CUSTOMER_NOT_FOUND"


class ReportSupplierNotFoundError(NotFoundError):
    """Raised when a Supplier Ledger request's `supplier_id` doesn't
    reference an existing supplier for the caller's tenant - also covers a
    supplier belonging to another tenant, indistinguishable from "does not
    exist" by design. Mirrors ReportCustomerNotFoundError exactly."""

    code = "REPORT_SUPPLIER_NOT_FOUND"
