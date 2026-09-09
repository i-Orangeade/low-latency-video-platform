from unittest.mock import AsyncMock

from app.services.zlm_service import zlm_service


def test_play_url_returns_http_flv(client) -> None:
    response = client.get("/api/streams/stream_001/play-url")
    assert response.status_code == 200
    payload = response.json()
    assert payload["stream_id"] == "stream_001"
    assert payload["protocol"] == "flv"
    assert payload["url"] == "http://127.0.0.1:8080/live/stream_001.live.flv"


def test_status_online(client, monkeypatch) -> None:
    monkeypatch.setattr(
        zlm_service,
        "get_stream_status",
        AsyncMock(
            return_value={
                "stream_id": "stream_001",
                "online": True,
                "app": "live",
                "schema_name": "rtmp",
                "origin_type": "rtmp_push",
                "reader_count": 1,
                "total_reader_count": 2,
                "tracks": [{"codec_id": 0}],
                "raw": {"schema": "rtmp"},
            }
        ),
    )

    response = client.get("/api/streams/stream_001/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["online"] is True
    assert payload["app"] == "live"


def test_status_offline(client, monkeypatch) -> None:
    monkeypatch.setattr(
        zlm_service,
        "get_stream_status",
        AsyncMock(
            return_value={
                "stream_id": "stream_001",
                "online": False,
                "app": "live",
                "reader_count": 0,
                "total_reader_count": 0,
                "tracks": [],
                "raw": {"code": 0, "data": []},
            }
        ),
    )

    response = client.get("/api/streams/stream_001/status")
    assert response.status_code == 200
    assert response.json()["online"] is False


def test_status_maps_zlm_errors_to_502(client, monkeypatch) -> None:
    monkeypatch.setattr(
        zlm_service,
        "get_stream_status",
        AsyncMock(side_effect=RuntimeError("zlm unavailable")),
    )

    response = client.get("/api/streams/stream_001/status")
    assert response.status_code == 502
    assert "failed to query ZLMediaKit" in response.json()["detail"]
