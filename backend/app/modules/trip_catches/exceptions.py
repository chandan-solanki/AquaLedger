from app.core.errors import BusinessRuleError, NotFoundError


class TripCatchNotFoundError(NotFoundError):
    code = "TRIP_CATCH_NOT_FOUND"


class TripCatchTripNotFoundError(NotFoundError):
    """Raised when a trip catch's trip_id doesn't reference an existing trip
    for the caller's tenant - also covers a trip belonging to another
    tenant, which is indistinguishable from "does not exist" by design."""

    code = "TRIP_CATCH_TRIP_NOT_FOUND"


class TripCatchFishNotFoundError(NotFoundError):
    """Raised when a trip catch's fish_id doesn't reference an existing fish
    for the caller's tenant."""

    code = "TRIP_CATCH_FISH_NOT_FOUND"


class TripCatchTripNotReturnedError(BusinessRuleError):
    """Raised when a trip catch is created against (or reassigned to) a trip
    that hasn't reached RETURNED status - fish can't be landed from a trip
    that hasn't come back yet."""

    code = "TRIP_CATCH_TRIP_NOT_RETURNED"


class TripCatchQuantityInvariantError(BusinessRuleError):
    """Raised when available_quantity + sold_quantity + waste_quantity would
    no longer equal quantity_caught after applying an update."""

    code = "TRIP_CATCH_QUANTITY_INVARIANT_VIOLATION"
