import hmac

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.device import Device
from app.schemas.record import RecordCreate
from app.schemas.zlm_hook import RecordMp4Payload, StreamChangedPayload, ZlmHookPayload
from app.services.alert_service import create_offline_alert_once, resolve_offline_alerts
from app.services.record_service import create_record_once

router = APIRouter(prefix="/zlm/hooks", tags=["zlm-hooks"])


def _authorized(payload: ZlmHookPayload, query_token: str | None = None) -> bool:
    supplied = query_token or payload.supplied_secret()
    expected = settings.zlm_hook_secret
    return bool(supplied and expected) and hmac.compare_digest(
        supplied.encode("utf-8"),
        expected.encode("utf-8"),
    )


def _rejected(message: str) -> dict[str, int | str]:
    return {"code": -1, "msg": message}


@router.post("/on_publish")
async def on_publish(
    payload: ZlmHookPayload,
    db: Session = Depends(get_db),
    hook_token: str | None = Query(default=None, alias="token"),
) -> dict[str, int | str]:
    if not _authorized(payload, hook_token):
        return _rejected("unauthorized hook")
    if not payload.stream:
        return _rejected("missing stream")
    device = (
        db.query(Device)
        .filter(Device.stream_id == payload.stream, Device.enabled.is_(True))
        .first()
    )
    if not device:
        return _rejected("unknown or disabled stream")
    return {"code": 0}


@router.post("/on_stream_changed")
async def on_stream_changed(
    payload: StreamChangedPayload,
    db: Session = Depends(get_db),
    hook_token: str | None = Query(default=None, alias="token"),
) -> dict[str, int | str]:
    if not _authorized(payload, hook_token):
        return _rejected("unauthorized hook")
    if not payload.stream:
        return _rejected("missing stream")

    device = db.query(Device).filter(Device.stream_id == payload.stream).first()
    if device:
        device.is_online = payload.regist
        db.commit()
        if payload.regist:
            resolve_offline_alerts(db, payload.stream)
        else:
            create_offline_alert_once(db, payload.stream)
    return {"code": 0}


@router.post("/on_record_mp4")
async def on_record_mp4(
    payload: RecordMp4Payload,
    db: Session = Depends(get_db),
    hook_token: str | None = Query(default=None, alias="token"),
) -> dict[str, int | str]:
    if not _authorized(payload, hook_token):
        return _rejected("unauthorized hook")
    if not payload.stream or not payload.file_path:
        return _rejected("missing stream or file path")

    create_record_once(
        db,
        RecordCreate(
            stream_id=payload.stream,
            file_path=payload.file_path,
            file_name=payload.file_name or payload.file_path.rsplit("/", 1)[-1],
            duration_seconds=payload.time_len,
            file_size_bytes=payload.file_size,
        ),
    )
    return {"code": 0}


@router.post("/on_flow_report")
def on_flow_report(
    payload: ZlmHookPayload,
    hook_token: str | None = Query(default=None, alias="token"),
) -> dict[str, int | str]:
    if not _authorized(payload, hook_token):
        return _rejected("unauthorized hook")
    return {"code": 0}


@router.post("/on_server_started")
def on_server_started(
    payload: ZlmHookPayload,
    hook_token: str | None = Query(default=None, alias="token"),
) -> dict[str, int | str]:
    if not _authorized(payload, hook_token):
        return _rejected("unauthorized hook")
    return {"code": 0}
