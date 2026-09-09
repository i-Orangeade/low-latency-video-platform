from typing import Any

import httpx

from app.config import settings


class ZlmService:
    def build_play_url(self, stream_id: str, app: str | None = None) -> str:
        app_name = app or settings.default_app
        host = settings.public_zlm_host
        http_port = settings.public_zlm_http_port
        return f"http://{host}:{http_port}/{app_name}/{stream_id}.live.flv"

    async def get_stream_status(self, stream_id: str, app: str | None = None) -> dict[str, Any]:
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
        url = f"{settings.zlm_base_url.rstrip('/')}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code", 0) != 0:
                raise RuntimeError(payload.get("msg") or f"ZLMediaKit API failed: {path}")
            return payload


zlm_service = ZlmService()
