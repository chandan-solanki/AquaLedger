from enum import StrEnum


class ExpenseType(StrEnum):
    DIESEL = "diesel"
    ICE = "ice"
    FOOD = "food"
    LABOUR = "labour"
    HARBOUR = "harbour"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    PERMIT = "permit"
    OTHER = "other"
