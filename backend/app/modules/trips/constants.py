from enum import StrEnum


class TripStatus(StrEnum):
    PLANNED = "planned"
    DEPARTED = "departed"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class TripType(StrEnum):
    FISHING = "fishing"
    TRANSPORT = "transport"
    MAINTENANCE = "maintenance"
    OTHER = "other"


# A boat may have at most one trip in these statuses at a time (Session 3
# business rule). RETURNED/CANCELLED trips no longer occupy the boat.
ACTIVE_TRIP_STATUSES = frozenset({TripStatus.PLANNED, TripStatus.DEPARTED})
