from fastapi import APIRouter

from app.api.error_handling import zlm_http_exception
from app.dependencies import StreamStatusServiceDep
from app.schemas.stream import PlayUrlResponse, StreamStatusResponse
from app.services.play_url_service import build_http_flv_url
from app.services.zlm_errors import ZlmError

router = APIRouter(prefix="/streams", tags=["streams"])


@router.get("/{stream_id}/play-url", response_model=PlayUrlResponse)
def get_play_url(stream_id: str) -> PlayUrlResponse:
    return PlayUrlResponse(
        stream_id=stream_id,
        protocol="flv",
        url=build_http_flv_url(stream_id),
    )


@router.get("/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(
    stream_id: str,
    stream_status_service: StreamStatusServiceDep,
) -> StreamStatusResponse:
    try:
        return await stream_status_service.get_status(stream_id)
    except ZlmError as exc:
        raise zlm_http_exception(exc) from exc
