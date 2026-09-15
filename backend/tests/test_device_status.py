from unittest.mock import AsyncMock

from app.services.zlm_service import zlm_service


def test_device_status_summary_returns_counts_and_details(client, monkeypatch) -> None:
    first = client.post(
        "/api/devices",
        json={"name": "Camera 1", "stream_id": "stream_001"},
    ).json()
    second = client.post(
        "/api/devices",
        json={"name": "Camera 2", "stream_id": "stream_002"},
    ).json()
    monkeypatch.setattr(
        zlm_service,
        "get_stream_statuses",
        AsyncMock(
            return_value={
                "stream_001": {
                    "stream_id": "stream_001",
                    "online": True,
                    "app": "live",
                    "schema_name": "rtmp",
                    "origin_type": "rtmp_push",
                    "reader_count": 2,
                    "total_reader_count": 3,
                    "tracks": [{"codec_id": 0}],
                },
                "stream_002": {
                    "stream_id": "stream_002",
                    "online": False,
                    "app": "live",
                    "reader_count": 0,
                    "total_reader_count": 0,
                    "tracks": [],
                },
            }
        ),
    )

    response = client.get("/api/devices/status")

    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "online": 1,
        "offline": 1,
        "devices": [
            {
                "id": second["id"],
                "name": "Camera 2",
                "stream_id": "stream_002",
                "online": False,
                "app": "live",
                "schema_name": None,
                "origin_type": None,
                "reader_count": 0,
                "total_reader_count": 0,
                "tracks": [],
            },
            {
                "id": first["id"],
                "name": "Camera 1",
                "stream_id": "stream_001",
                "online": True,
                "app": "live",
                "schema_name": "rtmp",
                "origin_type": "rtmp_push",
                "reader_count": 2,
                "total_reader_count": 3,
                "tracks": [{"codec_id": 0}],
            },
        ],
    }
    zlm_service.get_stream_statuses.assert_awaited_once_with(
        ["stream_002", "stream_001"]
    )


def test_device_status_summary_returns_empty_counts_without_devices(client, monkeypatch) -> None:
    get_statuses = AsyncMock()
    monkeypatch.setattr(zlm_service, "get_stream_statuses", get_statuses)

    response = client.get("/api/devices/status")

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "online": 0,
        "offline": 0,
        "devices": [],
    }
    get_statuses.assert_not_awaited()


def test_device_status_summary_maps_zlm_errors_to_502(client, monkeypatch) -> None:
    client.post(
        "/api/devices",
        json={"name": "Camera 1", "stream_id": "stream_001"},
    )
    monkeypatch.setattr(
        zlm_service,
        "get_stream_statuses",
        AsyncMock(side_effect=RuntimeError("zlm unavailable")),
    )

    response = client.get("/api/devices/status")

    assert response.status_code == 502
    assert "failed to query ZLMediaKit" in response.json()["detail"]
