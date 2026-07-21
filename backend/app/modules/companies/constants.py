from enum import StrEnum


class CompanyType(StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    BOTH = "both"


class OpeningBalanceType(StrEnum):
    """Which side of the ledger an opening balance sits on.

    DEBIT: the company owes us (receivable). CREDIT: we owe the company (payable).
    """

    DEBIT = "debit"
    CREDIT = "credit"


class CompanyStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
