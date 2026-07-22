from app.core.errors import BusinessRuleError, NotFoundError


class TripExpenseNotFoundError(NotFoundError):
    code = "TRIP_EXPENSE_NOT_FOUND"


class TripExpenseTripNotFoundError(NotFoundError):
    """Raised when a trip expense's trip_id doesn't reference an existing
    trip for the caller's tenant - also covers a trip belonging to another
    tenant, which is indistinguishable from "does not exist" by design."""

    code = "TRIP_EXPENSE_TRIP_NOT_FOUND"


class TripExpenseTripCancelledError(BusinessRuleError):
    """Raised when creating a new trip expense against a CANCELLED trip, or
    reassigning an existing expense's trip_id to one - cancelled trips
    cannot receive new expenses."""

    code = "TRIP_EXPENSE_TRIP_CANCELLED"


class TripExpenseDateBeforeDepartureError(BusinessRuleError):
    code = "TRIP_EXPENSE_DATE_BEFORE_DEPARTURE"


class TripExpenseDateAfterReturnError(BusinessRuleError):
    """Raised when expense_date is after the trip's actual_return_datetime.
    Trips that haven't returned yet (actual_return_datetime is NULL) have no
    upper bound."""

    code = "TRIP_EXPENSE_DATE_AFTER_RETURN"
