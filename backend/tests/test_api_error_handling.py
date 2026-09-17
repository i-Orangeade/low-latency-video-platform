import pytest

from app.api.error_handling import zlm_http_exception
from app.services.zlm_errors import (
    ZlmApiError,
    ZlmConnectionError,
    ZlmError,
    ZlmHttpError,
    ZlmResponseError,
)


def test_unknown_zlm_error_has_generic_upstream_response() -> None:
    exception = zlm_http_exception(ZlmError("unexpected upstream failure"))

    assert exception.status_code == 502
    assert exception.detail == {
        "code": "zlm_error",
        "message": "ZLMediaKit request failed",
        "reason": "unexpected upstream failure",
    }


@pytest.mark.parametrize(
    ("exception", "expected_status", "expected_code", "expected_message"),
    [
        (
            ZlmConnectionError("connection refused"),
            503,
            "zlm_unavailable",
            "ZLMediaKit is unavailable",
        ),
        (
            ZlmHttpError(502, "bad gateway"),
            502,
            "zlm_http_error",
            "ZLMediaKit returned HTTP 502",
        ),
        (
            ZlmApiError(-401, "invalid secret"),
            502,
            "zlm_api_error",
            "ZLMediaKit API request failed",
        ),
        (
            ZlmResponseError("data is not a list"),
            502,
            "zlm_response_error",
            "ZLMediaKit returned an invalid response",
        ),
    ],
)
def test_zlm_errors_map_to_stable_http_details(
    exception,
    expected_status,
    expected_code,
    expected_message,
) -> None:
    response = zlm_http_exception(exception)

    assert response.status_code == expected_status
    assert response.detail["code"] == expected_code
    assert response.detail["message"] == expected_message
    assert response.detail["reason"] == str(exception)

    if isinstance(exception, ZlmApiError):
        assert response.detail["zlm_code"] == -401
    else:
        assert "zlm_code" not in response.detail
