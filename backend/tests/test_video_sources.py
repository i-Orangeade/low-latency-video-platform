from types import SimpleNamespace

import pytest

from app.dependencies import get_stream_status_service
from app.schemas.stream import StreamStatus
from app.services.zlm_errors import ZlmConnectionError


def _stream_status_service(**methods):
    return SimpleNamespace(**methods)


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
    assert source["enabled"] is True
    assert source["created_at"]
    assert source["updated_at"]
    created_at = source["created_at"]
    updated_at = source["updated_at"]

    listed = client.get("/api/video-sources")
    assert listed.status_code == 200
    assert any(
        item["stream_id"] == "stream_001"
        for item in listed.json()["items"]
    )

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
        json={"name": "Source 1A", "enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Source 1A"
    assert updated.json()["enabled"] is False
    assert updated.json()["created_at"] == created_at
    assert updated.json()["updated_at"] != updated_at

    deleted = client.delete(f"/api/video-sources/{source['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/video-sources").json()["items"] == []


def test_list_video_sources_returns_paginated_response(client) -> None:
    for index in range(3):
        response = client.post(
            "/api/video-sources",
            json={"name": f"Source {index}", "stream_id": f"stream_{index}"},
        )
        assert response.status_code == 201

    response = client.get("/api/video-sources?page=2&page_size=2")

    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert response.json()["page_size"] == 2
    assert response.json()["total"] == 3
    assert response.json()["total_pages"] == 2
    assert [item["stream_id"] for item in response.json()["items"]] == ["stream_0"]


def test_list_video_sources_searches_name_and_stream_id(client) -> None:
    client.post(
        "/api/video-sources",
        json={"name": "Front Door Camera", "stream_id": "front_door"},
    )
    client.post(
        "/api/video-sources",
        json={"name": "Back Door Camera", "stream_id": "yard_camera"},
    )

    name_response = client.get("/api/video-sources?q=front")
    stream_response = client.get("/api/video-sources?q=yard_camera")

    assert [item["stream_id"] for item in name_response.json()["items"]] == ["front_door"]
    assert [item["stream_id"] for item in stream_response.json()["items"]] == ["yard_camera"]


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=0",
        "page_size=101",
    ],
)
def test_list_video_sources_rejects_invalid_pagination(client, query) -> None:
    response = client.get(f"/api/video-sources?{query}")

    assert response.status_code == 422


def test_list_video_sources_can_filter_enabled_state(client) -> None:
    enabled = client.post(
        "/api/video-sources",
        json={"name": "Enabled", "stream_id": "enabled_001"},
    ).json()
    disabled = client.post(
        "/api/video-sources",
        json={"name": "Disabled", "stream_id": "disabled_001", "enabled": False},
    ).json()

    response = client.get("/api/video-sources?enabled=false")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"] == [disabled]
    assert enabled not in response.json()["items"]


def test_get_missing_video_source_returns_404(client) -> None:
    response = client.get("/api/video-sources/999")
    assert response.status_code == 404


def test_update_missing_video_source_returns_404(client) -> None:
    response = client.put("/api/video-sources/999", json={"name": "missing"})
    assert response.status_code == 404


def test_video_source_crud_accepts_stream_id_reference(client) -> None:
    created = client.post(
        "/api/video-sources",
        json={"name": "Source 1", "stream_id": "api_test_001"},
    ).json()

    fetched = client.get("/api/video-sources/api_test_001")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]

    updated = client.put(
        "/api/video-sources/api_test_001",
        json={"enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False

    deleted = client.delete("/api/video-sources/api_test_001")
    assert deleted.status_code == 204


def test_video_source_status_summary_returns_empty_without_zlm_call(client) -> None:
    async def fail_if_called(stream_ids: list[str]):
        raise AssertionError("ZLMediaKit should not be queried when there are no video sources")

    stream_status_service = _stream_status_service(get_statuses=fail_if_called)
    client.app.dependency_overrides[get_stream_status_service] = lambda: stream_status_service

    response = client.get("/api/video-sources/status")

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "online": 0,
        "offline": 0,
        "video_sources": [],
    }


def test_video_source_status_summary(client) -> None:
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

    stream_status_service = _stream_status_service(get_statuses=fake_get_statuses)
    client.app.dependency_overrides[get_stream_status_service] = lambda: stream_status_service

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


def test_video_source_status_summary_maps_zlm_connection_errors_to_503(client) -> None:
    client.post(
        "/api/video-sources",
        json={"name": "Source 1", "stream_id": "stream_001"},
    )

    async def fake_get_statuses(stream_ids: list[str]):
        raise ZlmConnectionError("zlm unavailable")

    stream_status_service = _stream_status_service(get_statuses=fake_get_statuses)
    client.app.dependency_overrides[get_stream_status_service] = lambda: stream_status_service

    response = client.get("/api/video-sources/status")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "zlm_unavailable"


def test_video_source_status_summary_does_not_hide_internal_errors(client) -> None:
    client.post(
        "/api/video-sources",
        json={"name": "Source 1", "stream_id": "stream_001"},
    )

    async def fake_get_statuses(stream_ids: list[str]):
        raise ValueError("programming bug")

    stream_status_service = _stream_status_service(get_statuses=fake_get_statuses)
    client.app.dependency_overrides[get_stream_status_service] = lambda: stream_status_service

    response = client.get("/api/video-sources/status")

    assert response.status_code == 500


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
