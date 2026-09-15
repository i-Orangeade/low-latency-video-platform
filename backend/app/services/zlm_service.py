# ZLMediaKit 访问层。
# 该服务把 ZLM 的 URL 规则和 HTTP API 细节封装起来，API 路由层不需要关心 ZLM 参数格式。
from typing import Any

import httpx

from app.config import settings


class ZlmService:
    def build_play_url(self, stream_id: str, app: str | None = None) -> str:
        # ZLM 默认 HTTP-FLV 地址格式为：
        # http://<host>:<port>/<app>/<stream_id>.live.flv
        # app 与 stream_id 必须和 RTMP 推流路径保持一致，例如 /live/stream_001。
        app_name = app or settings.default_app
        host = settings.public_zlm_host
        http_port = settings.public_zlm_http_port
        return f"http://{host}:{http_port}/{app_name}/{stream_id}.live.flv"

    async def get_stream_status(self, stream_id: str, app: str | None = None) -> dict[str, Any]:
        # getMediaList 按 app 和 stream 查询 ZLM 当前托管的媒体流。
        # data 为空表示客户端尚未推流，或推流已经结束。
        app_name = app or settings.default_app
        payload = await self._get(
            "/index/api/getMediaList",
            {
                "secret": settings.zlm_secret,
                "vhost": "__defaultVhost__",
                "app": app_name,
                "stream": stream_id,
            },
        )

        data = payload.get("data") or []
        if not data:
            return {
                "stream_id": stream_id,
                "online": False,
                "app": app_name,
                "reader_count": 0,
                "total_reader_count": 0,
                "tracks": [],
                "raw": payload,
            }

        media = data[0]
        return {
            "stream_id": stream_id,
            "online": True,
            "app": media.get("app", app_name),
            "schema_name": media.get("schema"),
            "origin_type": media.get("originTypeStr"),
            "reader_count": media.get("readerCount", 0),
            "total_reader_count": media.get("totalReaderCount", 0),
            "tracks": media.get("tracks") or [],
            "raw": media,
        }

    async def _get(self, path: str, params: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
        # 统一封装 ZLM HTTP API 调用：
        # 1. HTTP 状态码异常时由 raise_for_status 抛出；
        # 2. HTTP 成功但 ZLM 的 code 非 0 时，转换成 RuntimeError。
        url = f"{settings.zlm_base_url.rstrip('/')}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code", 0) != 0:
                raise RuntimeError(payload.get("msg") or f"ZLMediaKit API failed: {path}")
            return payload


zlm_service = ZlmService()
