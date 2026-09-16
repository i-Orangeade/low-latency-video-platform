from typing import Any

import httpx

from app.config import settings
from app.services.zlm_errors import (
    ZlmApiError,
    ZlmConnectionError,
    ZlmHttpError,
    ZlmResponseError,
)


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
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise ZlmHttpError(status_code, f"ZLMediaKit HTTP {status_code}: {path}") from exc
        except httpx.RequestError as exc:
            raise ZlmConnectionError(f"failed to connect to ZLMediaKit: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ZlmResponseError(f"ZLMediaKit returned invalid JSON: {path}") from exc

        if not isinstance(payload, dict):
            raise ZlmResponseError(f"ZLMediaKit returned a non-object response: {path}")

        code = payload.get("code", 0)
        if code != 0:
            message = payload.get("msg") or f"ZLMediaKit API failed: {path}"
            raise ZlmApiError(code, str(message))

        return payload


zlm_client = ZlmClient()
