import asyncio
from unittest.mock import AsyncMock

from app.services.zlm_service import ZlmService


def test_get_stream_status_online_maps_media_list() -> None:
    service = ZlmService()
    service._get = AsyncMock(
        return_value={
            "code": 0,
            "data": [
                {
                    "app": "live",
                    "schema": "rtmp",
                    "originTypeStr": "rtmp_push",
                    "readerCount": 1,
                    "totalReaderCount": 3,
                    "tracks": [{"codec_id": 0}],
                }
            ],
        }
    )

    result = asyncio.run(service.get_stream_status("stream_001"))

    assert result["stream_id"] == "stream_001"
    assert result["online"] is True
    assert result["schema_name"] == "rtmp"
    assert result["origin_type"] == "rtmp_push"
    assert result["reader_count"] == 1
    service._get.assert_awaited_once()


def test_get_stream_status_offline_when_media_list_empty() -> None:
    service = ZlmService()
    service._get = AsyncMock(return_value={"code": 0, "data": []})

    result = asyncio.run(service.get_stream_status("stream_001"))

    assert result["online"] is False
    assert result["reader_count"] == 0


def test_get_stream_status_raises_when_zlm_returns_error_code() -> None:
    service = ZlmService()
    service._get = AsyncMock(side_effect=RuntimeError("unauthorized"))

    try:
        asyncio.run(service.get_stream_status("stream_001"))
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "unauthorized" in str(exc)
