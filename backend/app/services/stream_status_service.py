from typing import Any

from app.config import settings
from app.schemas.stream import StreamStatus, StreamStatusResponse
from app.services.zlm_errors import ZlmResponseError
from app.services.zlm_client import zlm_client


class StreamStatusService:
    """Maps ZLMediaKit media records into platform stream-status responses."""

    async def get_status(self, stream_id: str, app: str | None = None) -> StreamStatusResponse:
        app_name = app or settings.default_app
        payload = await zlm_client.get_media_list(app_name, stream_id)
        media_list = self._media_list(payload)
        if not media_list:
            return StreamStatusResponse(
                stream_id=stream_id,
                online=False,
                app=app_name,
                raw=payload,
            )

        media = self._find_media(stream_id, media_list)
        if not media:
            return StreamStatusResponse(
                stream_id=stream_id,
                online=False,
                app=app_name,
                raw=payload,
            )

        status = self._map_status(stream_id, app_name, media)
        return StreamStatusResponse(**status.model_dump(), raw=media)

    async def get_statuses(self, stream_ids: list[str], app: str | None = None) -> dict[str, StreamStatus]:
        app_name = app or settings.default_app
        payload = await zlm_client.get_media_list(app_name)
        media_by_stream = {
            str(media.get("stream")): media
            for media in self._media_list(payload)
            if media.get("stream") is not None
        }

        return {
            stream_id: self._map_status(stream_id, app_name, media_by_stream.get(stream_id))
            for stream_id in stream_ids
        }

    def _map_status(
        self,
        stream_id: str,
        app_name: str,
        media: dict[str, Any] | None,
    ) -> StreamStatus:
        if not media:
            return StreamStatus(stream_id=stream_id, online=False, app=app_name)

        return StreamStatus(
            stream_id=stream_id,
            online=True,
            app=str(media.get("app") or app_name),
            schema_name=media.get("schema"),
            origin_type=media.get("originTypeStr"),
            reader_count=media.get("readerCount", 0),
            total_reader_count=media.get("totalReaderCount", 0),
            tracks=media.get("tracks") or [],
        )

    def _media_list(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data")
        if not isinstance(data, list):
            raise ZlmResponseError("ZLMediaKit getMediaList response field 'data' must be a list")
        return [item for item in data if isinstance(item, dict)]

    def _find_media(
        self,
        stream_id: str,
        media_list: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for media in media_list:
            if media.get("stream") == stream_id:
                return media
        return None


stream_status_service = StreamStatusService()
