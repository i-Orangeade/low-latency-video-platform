class ZlmError(RuntimeError):
    """Base error for failures while talking to ZLMediaKit."""


class ZlmConnectionError(ZlmError):
    """ZLMediaKit could not be reached or timed out."""


class ZlmHttpError(ZlmError):
    """ZLMediaKit returned a non-success HTTP status."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class ZlmApiError(ZlmError):
    """ZLMediaKit returned a successful HTTP response with a non-zero API code."""

    def __init__(self, code: int | str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ZlmResponseError(ZlmError):
    """ZLMediaKit returned data that the platform cannot parse safely."""
