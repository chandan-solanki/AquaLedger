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


class TripCatchInsufficientQuantityError(BusinessRuleError):
    """Raised when a requested deduction (Sprint 9's invoice issue workflow,
    TripCatchService.deduct_available_quantity) exceeds available_quantity,
    checked under a `SELECT ... FOR UPDATE` lock so it can never allow
    available_quantity to go negative under concurrency.

    Sprint 15 Session 6: always raised with `details = {trip_catch_id,
    requested_quantity, available_quantity}` (all decimal-as-string, per
    ARCHITECTURE.md §5.1) so a caller can surface the conflict without a
    second lookup."""

    code = "TRIP_CATCH_INSUFFICIENT_QUANTITY"


class FishStockFishNotFoundError(NotFoundError):
    """Raised by GET /fish-stock/{fish_id} when fish_id doesn't reference an
    existing, non-deleted fish for the caller's tenant - also covers a fish
    belonging to another tenant, indistinguishable from "does not exist" by
    design (Sprint 15 Session 2)."""

    code = "FISH_STOCK_FISH_NOT_FOUND"
