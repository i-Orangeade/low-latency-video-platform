from typing import Any

import httpx

from app.config import settings


class ZlmClient:
    """Thin HTTP client for ZLMediaKit control APIs."""

    async def get_media_list(self, app: str | None = None, stream: str | None = None) -> dict[str, Any]:
        app_name = app or settings.default_app
        params: dict[str, Any] = {
            "secret": settings.zlm_secret,
            "vhost": "__defaultVhost__",
            "app": app_name,
        }
        if stream is not None:
            params["stream"] = stream

        return await self._get("/index/api/getMediaList", params)

    async def _get(self, path: str, params: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
        url = f"{settings.zlm_base_url.rstrip('/')}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code", 0) != 0:
                raise RuntimeError(payload.get("msg") or f"ZLMediaKit API failed: {path}")
            return payload


zlm_client = ZlmClient()
