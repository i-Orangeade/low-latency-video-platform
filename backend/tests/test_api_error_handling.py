from app.api.error_handling import zlm_http_exception
from app.services.zlm_errors import ZlmError


def test_unknown_zlm_error_has_generic_upstream_response() -> None:
    exception = zlm_http_exception(ZlmError("unexpected upstream failure"))

    assert exception.status_code == 502
    assert exception.detail == {
        "code": "zlm_error",
        "message": "ZLMediaKit request failed",
        "reason": "unexpected upstream failure",
    }
