from unittest.mock import AsyncMock

from app.schemas.stream import StreamStatusResponse
from app.services.stream_status_service import stream_status_service
import pytest

from app.services.zlm_errors import (
    ZlmApiError,
    ZlmConnectionError,
    ZlmHttpError,
    ZlmResponseError,
)


def test_play_url_returns_http_flv(client) -> None:
    response = client.get("/api/streams/stream_001/play-url")
    assert response.status_code == 200
    payload = response.json()
    assert payload["stream_id"] == "stream_001"
    assert payload["protocol"] == "flv"
    assert payload["url"] == "http://127.0.0.1:8080/live/stream_001.live.flv"


def test_status_online(client, monkeypatch) -> None:
    monkeypatch.setattr(
        stream_status_service,
        "get_status",
        AsyncMock(
            return_value=StreamStatusResponse(
                stream_id="stream_001",
                online=True,
                app="live",
                schema_name="rtmp",
                origin_type="rtmp_push",
                reader_count=1,
                total_reader_count=2,
                tracks=[{"codec_id": 0}],
                raw={"schema": "rtmp"},
            )
        ),
    )

    response = client.get("/api/streams/stream_001/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["online"] is True
    assert payload["app"] == "live"


def test_status_offline(client, monkeypatch) -> None:
    monkeypatch.setattr(
        stream_status_service,
        "get_status",
        AsyncMock(
            return_value=StreamStatusResponse(
                stream_id="stream_001",
                online=False,
                app="live",
                reader_count=0,
                total_reader_count=0,
                tracks=[],
                raw={"code": 0, "data": []},
            )
        ),
    )

    response = client.get("/api/streams/stream_001/status")
    assert response.status_code == 200
    assert response.json()["online"] is False


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (ZlmConnectionError("zlm unavailable"), 503, "zlm_unavailable"),
        (ZlmHttpError(500, "upstream failed"), 502, "zlm_http_error"),
        (ZlmApiError(-1, "bad secret"), 502, "zlm_api_error"),
        (ZlmResponseError("invalid payload"), 502, "zlm_response_error"),
    ],
)
def test_status_maps_zlm_errors_to_precise_api_errors(
    client,
    monkeypatch,
    error,
    expected_status,
    expected_code,
) -> None:
    monkeypatch.setattr(
        stream_status_service,
        "get_status",
        AsyncMock(side_effect=error),
    )

    response = client.get("/api/streams/stream_001/status")
    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code
    assert response.json()["detail"]["reason"] == str(error)


def test_status_api_error_includes_zlm_code(client, monkeypatch) -> None:
    error = ZlmApiError(-401, "bad secret")
    monkeypatch.setattr(
        stream_status_service,
        "get_status",
        AsyncMock(side_effect=error),
    )

    response = client.get("/api/streams/stream_001/status")

    assert response.status_code == 502
    assert response.json()["detail"]["zlm_code"] == -401


def test_status_does_not_hide_internal_errors(client, monkeypatch) -> None:
    monkeypatch.setattr(
        stream_status_service,
        "get_status",
        AsyncMock(side_effect=ValueError("programming bug")),
    )

    response = client.get("/api/streams/stream_001/status")
    assert response.status_code == 500
