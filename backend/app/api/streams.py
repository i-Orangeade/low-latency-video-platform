from fastapi import APIRouter, HTTPException

from app.schemas.stream import PlayUrlResponse, StreamStatusResponse
from app.services.play_url_service import build_http_flv_url
from app.services.stream_status_service import stream_status_service

router = APIRouter(prefix="/streams", tags=["streams"])


@router.get("/{stream_id}/play-url", response_model=PlayUrlResponse)
def get_play_url(stream_id: str) -> PlayUrlResponse:
    return PlayUrlResponse(
        stream_id=stream_id,
        protocol="flv",
        url=build_http_flv_url(stream_id),
    )


@router.get("/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(stream_id: str) -> StreamStatusResponse:
    try:
        return await stream_status_service.get_status(stream_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"failed to query ZLMediaKit: {exc}") from exc
