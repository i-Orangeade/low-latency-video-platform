from fastapi import HTTPException, status

from app.services.zlm_errors import (
    ZlmApiError,
    ZlmConnectionError,
    ZlmError,
    ZlmHttpError,
    ZlmResponseError,
)


def zlm_http_exception(exc: ZlmError) -> HTTPException:
    """Convert a known ZLMediaKit failure into a stable API error response."""
    if isinstance(exc, ZlmConnectionError):
        error_code = "zlm_unavailable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        message = "ZLMediaKit is unavailable"
    elif isinstance(exc, ZlmHttpError):
        error_code = "zlm_http_error"
        http_status = status.HTTP_502_BAD_GATEWAY
        message = f"ZLMediaKit returned HTTP {exc.status_code}"
    elif isinstance(exc, ZlmApiError):
        error_code = "zlm_api_error"
        http_status = status.HTTP_502_BAD_GATEWAY
        message = "ZLMediaKit API request failed"
    elif isinstance(exc, ZlmResponseError):
        error_code = "zlm_response_error"
        http_status = status.HTTP_502_BAD_GATEWAY
        message = "ZLMediaKit returned an invalid response"
    else:
        error_code = "zlm_error"
        http_status = status.HTTP_502_BAD_GATEWAY
        message = "ZLMediaKit request failed"

    detail = {
        "code": error_code,
        "message": message,
        "reason": str(exc),
    }
    if isinstance(exc, ZlmApiError):
        detail["zlm_code"] = exc.code

    return HTTPException(status_code=http_status, detail=detail)
