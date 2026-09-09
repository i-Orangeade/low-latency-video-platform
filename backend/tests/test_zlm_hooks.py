from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.zlm_hooks import router
from app.config import settings
from app.database import Base, get_db
from app.models.alert import Alert
from app.models.device import Device
from app.models.record import Record

HOOK_SECRET = "test-hook-secret"


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db: Session, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "zlm_hook_secret", HOOK_SECRET)
    app = FastAPI()
    app.include_router(router, prefix="/api")

    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def add_device(db: Session, stream_id: str, enabled: bool = True) -> Device:
    device = Device(name=stream_id, stream_id=stream_id, enabled=enabled)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def test_on_publish_accepts_enabled_device_and_both_secret_locations(
    client: TestClient,
    db: Session,
) -> None:
    add_device(db, "drone-1")

    direct = client.post(
        "/api/zlm/hooks/on_publish",
        json={"stream": "drone-1", "secret": HOOK_SECRET},
    )
    admin_params = client.post(
        "/api/zlm/hooks/on_publish",
        json={"stream": "drone-1", "admin_params": f"token=x&secret={HOOK_SECRET}"},
    )
    query_token = client.post(
        f"/api/zlm/hooks/on_publish?token={HOOK_SECRET}",
        json={"stream": "drone-1"},
    )

    assert direct.json() == {"code": 0}
    assert admin_params.json() == {"code": 0}
    assert query_token.json() == {"code": 0}


@pytest.mark.parametrize(
    ("stream_id", "enabled", "secret"),
    [
        ("unknown", True, HOOK_SECRET),
        ("disabled", False, HOOK_SECRET),
        ("enabled", True, "wrong-secret"),
    ],
)
def test_on_publish_rejects_unauthorized_or_unavailable_stream(
    client: TestClient,
    db: Session,
    stream_id: str,
    enabled: bool,
    secret: str,
) -> None:
    if stream_id != "unknown":
        add_device(db, stream_id, enabled=enabled)

    response = client.post(
        "/api/zlm/hooks/on_publish",
        json={"stream": stream_id, "secret": secret},
    )

    assert response.status_code == 200
    assert response.json()["code"] == -1


def test_stream_changed_updates_state_and_deduplicates_offline_alert(
    client: TestClient,
    db: Session,
) -> None:
    device = add_device(db, "drone-2")
    payload = {"stream": "drone-2", "secret": HOOK_SECRET}

    online = client.post(
        "/api/zlm/hooks/on_stream_changed",
        json={**payload, "regist": True},
    )
    first_offline = client.post(
        "/api/zlm/hooks/on_stream_changed",
        json={**payload, "regist": False},
    )
    duplicate_offline = client.post(
        "/api/zlm/hooks/on_stream_changed",
        json={**payload, "regist": False},
    )

    db.refresh(device)
    alerts = db.query(Alert).filter(Alert.stream_id == "drone-2").all()
    assert online.json() == {"code": 0}
    assert first_offline.json() == {"code": 0}
    assert duplicate_offline.json() == {"code": 0}
    assert device.is_online is False
    assert len(alerts) == 1
    assert alerts[0].category == "stream_offline"
    assert alerts[0].is_read is False


def test_record_hook_is_idempotent_and_validates_payload(
    client: TestClient,
    db: Session,
) -> None:
    payload = {
        "stream": "drone-3",
        "secret": HOOK_SECRET,
        "file_path": "/record/drone-3/clip.mp4",
        "file_name": "clip.mp4",
        "time_len": "12.8",
        "file_size": "2048",
    }

    first = client.post("/api/zlm/hooks/on_record_mp4", json=payload)
    duplicate = client.post("/api/zlm/hooks/on_record_mp4", json=payload)
    malformed = client.post(
        "/api/zlm/hooks/on_record_mp4",
        json={**payload, "file_path": "/record/bad.mp4", "file_size": "NaN"},
    )
    wrong_type = client.post(
        "/api/zlm/hooks/on_record_mp4",
        json={**payload, "file_path": "/record/type.mp4", "file_size": {}},
    )

    records = db.query(Record).all()
    assert first.json() == {"code": 0}
    assert duplicate.json() == {"code": 0}
    assert len(records) == 1
    assert records[0].duration_seconds == 12
    assert records[0].file_size_bytes == 2048
    assert malformed.status_code == 422
    assert wrong_type.status_code == 422
