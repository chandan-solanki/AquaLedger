from app.core.errors import ConflictError, NotFoundError


class FishNotFoundError(NotFoundError):
    code = "FISH_NOT_FOUND"


class DuplicateFishCodeError(ConflictError):
    code = "DUPLICATE_FISH_CODE"


class DuplicateFishNameError(ConflictError):
    code = "DUPLICATE_FISH_NAME"
