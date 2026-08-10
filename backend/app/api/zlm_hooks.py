from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.alert import AlertCreate
from app.schemas.record import RecordCreate
from app.services.alert_service import create_alert
from app.services.record_service import create_record

router = APIRouter(prefix="/zlm/hooks", tags=["zlm-hooks"])


@router.post("/on_publish")
def on_publish(payload: dict[str, Any]) -> dict[str, int]:
    return {"code": 0}


@router.post("/on_stream_changed")
def on_stream_changed(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, int]:
    if payload.get("regist") is False:
        stream_id = payload.get("stream") or "unknown"
        create_alert(
            db,
            AlertCreate(
                stream_id=stream_id,
                level="warning",
                category="stream_offline",
                message=f"Stream {stream_id} is offline.",
            ),
        )
    return {"code": 0}


@router.post("/on_record_mp4")
def on_record_mp4(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, int]:
    file_path = payload.get("file_path") or payload.get("filePath")
    file_name = payload.get("file_name") or payload.get("fileName") or file_path or "unknown.mp4"
    if file_path:
        create_record(
            db,
            RecordCreate(
                stream_id=payload.get("stream") or "unknown",
                file_path=file_path,
                file_name=file_name,
                duration_seconds=int(float(payload.get("time_len") or payload.get("timeLen") or 0)),
                file_size_bytes=int(payload.get("file_size") or payload.get("fileSize") or 0),
            ),
        )
    return {"code": 0}


@router.post("/on_flow_report")
def on_flow_report(payload: dict[str, Any]) -> dict[str, int]:
    return {"code": 0}


@router.post("/on_server_started")
def on_server_started(payload: dict[str, Any]) -> dict[str, int]:
    return {"code": 0}
