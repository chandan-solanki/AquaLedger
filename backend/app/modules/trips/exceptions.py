from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class TripNotFoundError(NotFoundError):
    code = "TRIP_NOT_FOUND"


class DuplicateTripNumberError(ConflictError):
    code = "DUPLICATE_TRIP_NUMBER"


class TripBoatNotFoundError(NotFoundError):
    """Raised when a trip's boat_id doesn't reference an existing boat
    for the caller's tenant - also covers a boat belonging to another
    tenant, which is indistinguishable from "does not exist" by design."""

    code = "TRIP_BOAT_NOT_FOUND"


class TripBoatNotActiveError(BusinessRuleError):
    code = "TRIP_BOAT_NOT_ACTIVE"


class TripBoatAlreadyActiveError(BusinessRuleError):
    """Raised when the boat already has another non-deleted trip in
    PLANNED/DEPARTED status (ACTIVE_TRIP_STATUSES)."""

    code = "TRIP_BOAT_ALREADY_ACTIVE"


class TripInvalidReturnDatetimeError(BusinessRuleError):
    code = "TRIP_INVALID_RETURN_DATETIME"


class TripBoatChangeNotAllowedError(ConflictError):
    """Raised when trying to reassign the boat of a trip that is already
    RETURNED - a state-machine violation, same category as editing an
    issued invoice (see ConflictError's docstring in app.core.errors)."""

    code = "TRIP_BOAT_CHANGE_NOT_ALLOWED"
