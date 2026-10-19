import pytest

from app.config import settings

HOOK_SECRET = "test-hook-secret"


@pytest.fixture(autouse=True)
def configure_hook_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "zlm_hook_secret", HOOK_SECRET)


def register_source(client, stream_id: str, enabled: bool = True) -> None:
    response = client.post(
        "/api/video-sources",
        json={"name": stream_id, "stream_id": stream_id, "enabled": enabled},
    )
    assert response.status_code == 201


def publish_payload(stream_id: str | None, app: str | None = "live") -> dict:
    return {
        "mediaServerId": "llvp-zlm",
        "app": app,
        "stream": stream_id,
        "schema": "rtmp",
    }


def test_on_publish_accepts_registered_enabled_source(client) -> None:
    register_source(client, "allowed_001")

    response = client.post(
        f"/api/zlm/hooks/on_publish?token={HOOK_SECRET}",
        json=publish_payload("allowed_001"),
    )

    assert response.status_code == 200
    assert response.json() == {"code": 0, "msg": "success"}


@pytest.mark.parametrize(
    ("stream_id", "enabled", "app"),
    [
        ("disabled_001", False, "live"),
        ("unknown_001", True, "live"),
        ("wrong_app_001", True, "other"),
        (None, True, "live"),
    ],
)
def test_on_publish_rejects_unavailable_or_invalid_streams(
    client,
    stream_id: str | None,
    enabled: bool,
    app: str,
) -> None:
    if stream_id and stream_id != "unknown_001":
        register_source(client, stream_id, enabled=enabled)

    response = client.post(
        f"/api/zlm/hooks/on_publish?token={HOOK_SECRET}",
        json=publish_payload(stream_id, app=app),
    )

    assert response.status_code == 200
    assert response.json()["code"] == -1


@pytest.mark.parametrize(
    "token",
    [None, "", "wrong-secret"],
)
def test_on_publish_rejects_unauthorized_hook_calls(client, token: str | None) -> None:
    register_source(client, "allowed_002")
    suffix = "" if token is None else f"?token={token}"

    response = client.post(
        f"/api/zlm/hooks/on_publish{suffix}",
        json=publish_payload("allowed_002"),
    )

    assert response.status_code == 200
    assert response.json() == {"code": -1, "msg": "unauthorized hook"}


def test_on_publish_does_not_accept_payload_secret(client) -> None:
    register_source(client, "allowed_003")

    response = client.post(
        "/api/zlm/hooks/on_publish",
        json={**publish_payload("allowed_003"), "secret": HOOK_SECRET},
    )

    assert response.status_code == 200
    assert response.json() == {"code": -1, "msg": "unauthorized hook"}


def test_on_publish_fails_closed_when_hook_secret_is_not_configured(
    client,
    monkeypatch,
) -> None:
    register_source(client, "allowed_004")
    monkeypatch.setattr(settings, "zlm_hook_secret", None)

    response = client.post(
        f"/api/zlm/hooks/on_publish?token={HOOK_SECRET}",
        json=publish_payload("allowed_004"),
    )

    assert response.status_code == 200
    assert response.json() == {"code": -1, "msg": "unauthorized hook"}
