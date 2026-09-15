# 媒体流辅助 API。
# 这里不转发视频数据，只负责告诉前端播放地址，以及向 ZLM 查询当前流状态。
from fastapi import APIRouter, HTTPException

from app.schemas.stream import PlayUrlResponse, StreamStatusResponse
from app.services.zlm_service import zlm_service

router = APIRouter(prefix="/streams", tags=["streams"])


@router.get("/{stream_id}/play-url", response_model=PlayUrlResponse)
def get_play_url(stream_id: str) -> PlayUrlResponse:
    # 后端生成的是浏览器可直接访问的 HTTP-FLV 地址。
    # 真正的视频数据由浏览器向 ZLMediaKit 建立连接后直接拉取，不经过 FastAPI。
    return PlayUrlResponse(
        stream_id=stream_id,
        protocol="flv",
        url=zlm_service.build_play_url(stream_id),
    )


@router.get("/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(stream_id: str) -> dict:
    try:
        # zlm_service 内部调用 ZLM 的 getMediaList API，并整理成前端需要的字段。
        return await zlm_service.get_stream_status(stream_id)
    except Exception as exc:
        # ZLM 是外部服务。它超时、拒绝连接或返回错误时，对调用方而言属于上游网关故障。
        # 返回 502，既保留错误原因，也避免把完整堆栈直接暴露给浏览器。
        raise HTTPException(status_code=502, detail=f"failed to query ZLMediaKit: {exc}") from exc
