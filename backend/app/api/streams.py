from fastapi import APIRouter, HTTPException, Query

from app.schemas.stream import PlayUrlResponse, StreamStatusResponse
from app.services.zlm_service import zlm_service

router = APIRouter(prefix="/streams", tags=["streams"])

SUPPORTED_PROTOCOLS = {"flv", "webrtc", "hls", "rtmp", "rtsp"}


@router.get("/{stream_id}/play-url", response_model=PlayUrlResponse)
def get_play_url(
    stream_id: str,
    protocol: str = Query("flv", pattern="^(flv|webrtc|hls|rtmp|rtsp)$"),
) -> PlayUrlResponse:
    if protocol not in SUPPORTED_PROTOCOLS:
        raise HTTPException(status_code=400, detail="unsupported protocol")
    return PlayUrlResponse(
        stream_id=stream_id,
        protocol=protocol,
        url=zlm_service.build_play_url(stream_id, protocol),
    )


@router.get("/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(stream_id: str) -> dict:
    try:
        return await zlm_service.get_stream_status(stream_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"failed to query ZLMediaKit: {exc}") from exc


@router.post("/{stream_id}/start-record")
async def start_record(stream_id: str) -> dict:
    try:
        return await zlm_service.start_record(stream_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"failed to start record: {exc}") from exc


@router.post("/{stream_id}/stop-record")
async def stop_record(stream_id: str) -> dict:
    try:
        return await zlm_service.stop_record(stream_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"failed to stop record: {exc}") from exc
