import pytest


def test_device_crud(client) -> None:
    created = client.post(
        "/api/devices",
        json={"name": "Camera 1", "stream_id": "stream_001"},
    )
    assert created.status_code == 201
    device = created.json()
    assert device["id"]
    assert device["name"] == "Camera 1"
    assert device["stream_id"] == "stream_001"

    listed = client.get("/api/devices")
    assert listed.status_code == 200
    assert any(item["stream_id"] == "stream_001" for item in listed.json())

    duplicate = client.post(
        "/api/devices",
        json={"name": "Camera 2", "stream_id": "stream_001"},
    )
    assert duplicate.status_code == 409

    updated = client.put(
        f"/api/devices/{device['id']}",
        json={"name": "Camera 1A"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Camera 1A"

    deleted = client.delete(f"/api/devices/{device['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/devices").json() == []


def test_update_missing_device_returns_404(client) -> None:
    response = client.put("/api/devices/999", json={"name": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "device not found"


def test_delete_missing_device_returns_404(client) -> None:
    response = client.delete("/api/devices/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "device not found"


def test_create_device_rejects_duplicate_stream_id(client) -> None:
    client.post(
        "/api/devices",
        json={"name": "Camera 1", "stream_id": "stream_001"},
    )

    response = client.post(
        "/api/devices",
        json={"name": "Camera 2", "stream_id": "stream_001"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "stream_id already exists"


def test_update_device_rejects_duplicate_stream_id(client) -> None:
    first = client.post(
        "/api/devices",
        json={"name": "Camera 1", "stream_id": "stream_001"},
    ).json()
    second = client.post(
        "/api/devices",
        json={"name": "Camera 2", "stream_id": "stream_002"},
    ).json()

    response = client.put(
        f"/api/devices/{second['id']}",
        json={"stream_id": first["stream_id"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "stream_id already exists"


def test_update_device_allows_keeping_its_own_stream_id(client) -> None:
    created = client.post(
        "/api/devices",
        json={"name": "Camera 1", "stream_id": "stream_001"},
    ).json()

    response = client.put(
        f"/api/devices/{created['id']}",
        json={"name": "Camera 1A", "stream_id": "stream_001"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Camera 1A"
    assert response.json()["stream_id"] == "stream_001"


def test_get_device_returns_device(client) -> None:
    created = client.post(
        "/api/devices",
        json={"name": "Camera 1", "stream_id": "stream_001"},
    )
    device_id = created.json()["id"]

    response = client.get(f"/api/devices/{device_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": device_id,
        "name": "Camera 1",
        "stream_id": "stream_001",
    }


def test_get_missing_device_returns_404(client) -> None:
    response = client.get("/api/devices/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "device not found"


def test_create_device_strips_text_fields(client) -> None:
    response = client.post(
        "/api/devices",
        json={"name": "  Camera 1  ", "stream_id": "  stream_001  "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Camera 1"
    assert response.json()["stream_id"] == "stream_001"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "stream_id": "stream_001"},
        {"name": "   ", "stream_id": "stream_001"},
        {"name": None, "stream_id": "stream_001"},
        {"name": "Camera 1", "stream_id": ""},
        {"name": "Camera 1", "stream_id": None},
        {"name": "Camera 1", "stream_id": "stream 001"},
        {"name": "Camera 1", "stream_id": "stream/001"},
        {"name": "Camera 1", "stream_id": "stream.001"},
        {"name": "x" * 101, "stream_id": "stream_001"},
        {"name": "Camera 1", "stream_id": "s" * 101},
    ],
)
def test_create_device_rejects_invalid_fields(client, payload) -> None:
    response = client.post("/api/devices", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": "   "},
        {"name": None},
        {"stream_id": ""},
        {"stream_id": None},
        {"stream_id": "stream 001"},
        {"stream_id": "stream/001"},
        {"stream_id": "s" * 101},
    ],
)
def test_update_device_rejects_invalid_fields(client, payload) -> None:
    created = client.post(
        "/api/devices",
        json={"name": "Camera 1", "stream_id": "stream_001"},
    )
    device_id = created.json()["id"]

    response = client.put(f"/api/devices/{device_id}", json=payload)

    assert response.status_code == 422
