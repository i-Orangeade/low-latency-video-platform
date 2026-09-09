from fastapi import APIRouter, HTTPException

from app.schemas.stream import PlayUrlResponse, StreamStatusResponse
from app.services.zlm_service import zlm_service

router = APIRouter(prefix="/streams", tags=["streams"])


@router.get("/{stream_id}/play-url", response_model=PlayUrlResponse)
def get_play_url(stream_id: str) -> PlayUrlResponse:
    return PlayUrlResponse(
        stream_id=stream_id,
        protocol="flv",
        url=zlm_service.build_play_url(stream_id),
    )


@router.get("/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(stream_id: str) -> dict:
    try:
        return await zlm_service.get_stream_status(stream_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"failed to query ZLMediaKit: {exc}") from exc
