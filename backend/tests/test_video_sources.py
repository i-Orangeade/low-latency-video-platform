import pytest

from app.schemas.stream import StreamStatus
from app.services.stream_status_service import stream_status_service


def test_video_source_crud(client) -> None:
    created = client.post(
        "/api/video-sources",
        json={"name": "Source 1", "stream_id": "stream_001"},
    )
    assert created.status_code == 201
    source = created.json()
    assert source["id"]
    assert source["name"] == "Source 1"
    assert source["stream_id"] == "stream_001"

    listed = client.get("/api/video-sources")
    assert listed.status_code == 200
    assert any(item["stream_id"] == "stream_001" for item in listed.json())

    fetched = client.get(f"/api/video-sources/{source['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["stream_id"] == "stream_001"

    duplicate = client.post(
        "/api/video-sources",
        json={"name": "Source 2", "stream_id": "stream_001"},
    )
    assert duplicate.status_code == 409

    updated = client.put(
        f"/api/video-sources/{source['id']}",
        json={"name": "Source 1A"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Source 1A"

    deleted = client.delete(f"/api/video-sources/{source['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/video-sources").json() == []


def test_get_missing_video_source_returns_404(client) -> None:
    response = client.get("/api/video-sources/999")
    assert response.status_code == 404


def test_update_missing_video_source_returns_404(client) -> None:
    response = client.put("/api/video-sources/999", json={"name": "missing"})
    assert response.status_code == 404


def test_video_source_status_summary_returns_empty_without_zlm_call(client, monkeypatch) -> None:
    async def fail_if_called(stream_ids: list[str]):
        raise AssertionError("ZLMediaKit should not be queried when there are no video sources")

    monkeypatch.setattr(stream_status_service, "get_statuses", fail_if_called)

    response = client.get("/api/video-sources/status")

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "online": 0,
        "offline": 0,
        "video_sources": [],
    }


def test_video_source_status_summary(client, monkeypatch) -> None:
    created_online = client.post(
        "/api/video-sources",
        json={"name": "Source 1", "stream_id": "stream_001"},
    ).json()
    created_offline = client.post(
        "/api/video-sources",
        json={"name": "Source 2", "stream_id": "stream_002"},
    ).json()

    async def fake_get_statuses(stream_ids: list[str]):
        assert stream_ids == ["stream_002", "stream_001"]
        return {
            "stream_001": StreamStatus(stream_id="stream_001", online=True, app="live"),
            "stream_002": StreamStatus(stream_id="stream_002", online=False, app="live"),
        }

    monkeypatch.setattr(stream_status_service, "get_statuses", fake_get_statuses)

    response = client.get("/api/video-sources/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["online"] == 1
    assert payload["offline"] == 1
    assert payload["video_sources"] == [
        {
            "id": created_offline["id"],
            "name": "Source 2",
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
            "id": created_online["id"],
            "name": "Source 1",
            "stream_id": "stream_001",
            "online": True,
            "app": "live",
            "schema_name": None,
            "origin_type": None,
            "reader_count": 0,
            "total_reader_count": 0,
            "tracks": [],
        },
    ]


def test_video_source_status_summary_maps_zlm_errors_to_502(client, monkeypatch) -> None:
    client.post(
        "/api/video-sources",
        json={"name": "Source 1", "stream_id": "stream_001"},
    )

    async def fake_get_statuses(stream_ids: list[str]):
        raise RuntimeError("zlm unavailable")

    monkeypatch.setattr(stream_status_service, "get_statuses", fake_get_statuses)

    response = client.get("/api/video-sources/status")

    assert response.status_code == 502
    assert "failed to query ZLMediaKit" in response.json()["detail"]


def test_create_video_source_strips_text_fields(client) -> None:
    response = client.post(
        "/api/video-sources",
        json={"name": "  Source 1  ", "stream_id": "  stream_001  "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Source 1"
    assert response.json()["stream_id"] == "stream_001"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "stream_id": "stream_001"},
        {"name": "   ", "stream_id": "stream_001"},
        {"name": "Source 1", "stream_id": ""},
        {"name": "Source 1", "stream_id": "stream 001"},
        {"name": "Source 1", "stream_id": "stream/001"},
        {"name": "Source 1", "stream_id": "stream.001"},
        {"name": "x" * 101, "stream_id": "stream_001"},
        {"name": "Source 1", "stream_id": "s" * 101},
    ],
)
def test_create_video_source_rejects_invalid_fields(client, payload) -> None:
    response = client.post("/api/video-sources", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": "   "},
        {"stream_id": ""},
        {"stream_id": "stream 001"},
        {"stream_id": "stream/001"},
        {"stream_id": "s" * 101},
    ],
)
def test_update_video_source_rejects_invalid_fields(client, payload) -> None:
    created = client.post(
        "/api/video-sources",
        json={"name": "Source 1", "stream_id": "stream_001"},
    )
    source_id = created.json()["id"]

    response = client.put(f"/api/video-sources/{source_id}", json=payload)

    assert response.status_code == 422
