from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import configure_engine
from app.main import create_app
from app.services.auth_service import hash_password


@pytest.fixture
def auth_client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    configure_engine(f"sqlite:///{tmp_path}/llvp.db")
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(
        settings,
        "admin_password_hash",
        hash_password("correct horse battery staple"),
    )
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client


def test_login_fails_closed_when_admin_is_not_configured(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_username", None)
    monkeypatch.setattr(settings, "admin_password_hash", None)

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "administrator authentication is not configured"}


def test_login_fails_closed_when_password_hash_is_malformed(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password_hash", "not-a-supported-hash")

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "administrator authentication is not configured"}


def test_login_fails_closed_when_password_hash_has_invalid_base64(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password_hash", "scrypt:16384:8:1:a:a")

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "password"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "administrator authentication is not configured"}


def test_login_rejects_invalid_credentials_without_leaking_details(auth_client) -> None:
    response = auth_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid administrator credentials"}
    assert "correct horse" not in response.text
    assert "scrypt" not in response.text


def test_login_rejects_unicode_username_without_internal_error(auth_client) -> None:
    response = auth_client.post(
        "/api/auth/login",
        json={"username": "管理员", "password": "wrong password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid administrator credentials"}


def test_login_sets_http_only_session_cookie(auth_client) -> None:
    response = auth_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "admin"}
    assert response.headers["cache-control"] == "no-store"
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/api" in set_cookie
    assert "max-age=28800" in set_cookie

    session = auth_client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json() == {"authenticated": True, "username": "admin"}


def test_session_is_anonymous_without_a_valid_cookie(auth_client) -> None:
    auth_client.cookies.set(settings.auth_cookie_name, "not-a-real-session", path="/api")
    response = auth_client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "username": None}


def test_logout_revokes_the_current_session(auth_client) -> None:
    login = auth_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "correct horse battery staple"},
    )
    token = login.cookies[settings.auth_cookie_name]

    logout = auth_client.post("/api/auth/logout")

    assert logout.status_code == 204
    assert settings.auth_cookie_name not in auth_client.cookies
    auth_client.cookies.set(settings.auth_cookie_name, token, path="/api")
    session = auth_client.get("/api/auth/session")
    assert session.json() == {"authenticated": False, "username": None}


def test_login_request_fields_are_bounded(auth_client) -> None:
    response = auth_client.post(
        "/api/auth/login",
        json={"username": "a" * 101, "password": "p" * 1025},
    )

    assert response.status_code == 422


def test_login_rate_limits_repeated_failures(auth_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_login_max_attempts", 2)
    payload = {"username": "admin", "password": "wrong password"}

    assert auth_client.post("/api/auth/login", json=payload).status_code == 401
    assert auth_client.post("/api/auth/login", json=payload).status_code == 401
    response = auth_client.post("/api/auth/login", json=payload)

    assert response.status_code == 429
    assert response.json() == {"detail": "too many login attempts"}
    assert response.headers["retry-after"] == "900"
