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
