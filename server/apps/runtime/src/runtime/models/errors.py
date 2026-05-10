class ZenveError(Exception):
    """Base domain exception."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(ZenveError):
    pass


class ConflictError(ZenveError):
    pass


class ValidationError(ZenveError):
    pass


class ExternalError(ZenveError):
    pass


class RateLimitError(ZenveError):
    pass


class AuthError(ZenveError):
    pass
