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

    async def get_stream_qos(
        self,
        stream_id: str,
        probe_ms: int = 1000,
        app: str | None = None,
    ) -> dict[str, Any]:
        payload = await self._get(
            "/index/api/getStreamQos",
            {
                "secret": self.secret,
                "vhost": "__defaultVhost__",
                "app": app or settings.default_app,
                "stream": stream_id,
                "probe_ms": probe_ms,
            },
            timeout=max(5.0, probe_ms / 1000 + 3.0),
        )
        data = payload.get("data") or {}
        return {
            "stream_id": stream_id,
            "probe_ms": int(data.get("probeMs", probe_ms)),
            "bitrate_kbps": float(data.get("bitrateKbps", 0)),
            "video_fps": float(data.get("videoFps", 0)),
            "video_frame_count": int(data.get("videoFrameCount", 0)),
            "audio_frame_count": int(data.get("audioFrameCount", 0)),
            "key_frame_count": int(data.get("keyFrameCount", 0)),
            "average_gop_ms": data.get("averageGopMs"),
            "first_frame_delay_ms": data.get("firstFrameDelayMs"),
            "timestamp_rollback_count": int(data.get("timestampRollbackCount", 0)),
            "reader_count": int(data.get("readerCount", 0)),
            "total_reader_count": int(data.get("totalReaderCount", 0)),
            "current_bytes_speed": int(data.get("currentBytesSpeed", 0)),
            "alive_second": int(data.get("aliveSecond", 0)),
        }

    async def _get(
        self,
        path: str,
        params: dict[str, Any],
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code", 0) != 0:
                raise RuntimeError(payload.get("msg") or f"ZLMediaKit API failed: {path}")
            return payload


zlm_service = ZlmService()
