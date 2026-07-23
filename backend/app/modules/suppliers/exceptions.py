from app.core.errors import ConflictError, NotFoundError


class SupplierNotFoundError(NotFoundError):
    code = "SUPPLIER_NOT_FOUND"


class DuplicateSupplierCodeError(ConflictError):
    code = "DUPLICATE_SUPPLIER_CODE"


class DuplicateSupplierNameError(ConflictError):
    code = "DUPLICATE_SUPPLIER_NAME"
