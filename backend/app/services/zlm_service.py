from typing import Any

import httpx

from app.config import settings


class ZlmService:
    def __init__(self) -> None:
        self.base_url = settings.zlm_base_url.rstrip("/")
        self.secret = settings.zlm_secret

    def build_play_url(self, stream_id: str, protocol: str, app: str | None = None) -> str:
        app_name = app or settings.default_app
        host = settings.public_zlm_host
        http_port = settings.public_zlm_http_port

        if protocol == "flv":
            return f"http://{host}:{http_port}/{app_name}/{stream_id}.live.flv"
        if protocol == "hls":
            return f"http://{host}:{http_port}/{app_name}/{stream_id}/hls.m3u8"
        if protocol == "webrtc":
            return (
                f"http://{host}:{http_port}/index/api/webrtc"
                f"?app={app_name}&stream={stream_id}&type=play"
            )
        if protocol == "rtmp":
            return f"rtmp://{host}:{settings.public_zlm_rtmp_port}/{app_name}/{stream_id}"
        if protocol == "rtsp":
            return f"rtsp://{host}:{settings.public_zlm_rtsp_port}/{app_name}/{stream_id}"
        raise ValueError(f"Unsupported protocol: {protocol}")

    async def get_stream_status(self, stream_id: str, app: str | None = None) -> dict[str, Any]:
        app_name = app or settings.default_app
        payload = await self._get(
            "/index/api/getMediaList",
            {
                "secret": self.secret,
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

    async def start_record(self, stream_id: str, app: str | None = None) -> dict[str, Any]:
        return await self._get(
            "/index/api/startRecord",
            {
                "secret": self.secret,
                "type": 1,
                "vhost": "__defaultVhost__",
                "app": app or settings.default_app,
                "stream": stream_id,
            },
        )

    async def stop_record(self, stream_id: str, app: str | None = None) -> dict[str, Any]:
        return await self._get(
            "/index/api/stopRecord",
            {
                "secret": self.secret,
                "type": 1,
                "vhost": "__defaultVhost__",
                "app": app or settings.default_app,
                "stream": stream_id,
            },
        )

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()


zlm_service = ZlmService()
