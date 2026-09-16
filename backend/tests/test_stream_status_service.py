import asyncio
from unittest.mock import AsyncMock

import pytest

from app.services.stream_status_service import StreamStatusService
from app.services.zlm_client import ZlmClient, zlm_client


def test_get_stream_status_online_maps_media_list(monkeypatch) -> None:
    service = StreamStatusService()
    get_media_list = AsyncMock(
        return_value={
            "code": 0,
            "data": [
                {
                    "app": "live",
                    "stream": "stream_001",
                    "schema": "rtmp",
                    "originTypeStr": "rtmp_push",
                    "readerCount": 1,
                    "totalReaderCount": 3,
                    "tracks": [{"codec_id": 0}],
                }
            ],
        }
    )
    monkeypatch.setattr(zlm_client, "get_media_list", get_media_list)

    result = asyncio.run(service.get_status("stream_001"))

    assert result.stream_id == "stream_001"
    assert result.online is True
    assert result.schema_name == "rtmp"
    assert result.origin_type == "rtmp_push"
    assert result.reader_count == 1
    assert result.raw["schema"] == "rtmp"
    get_media_list.assert_awaited_once_with("live", "stream_001")


def test_get_stream_status_offline_when_media_list_empty(monkeypatch) -> None:
    service = StreamStatusService()
    get_media_list = AsyncMock(return_value={"code": 0, "data": []})
    monkeypatch.setattr(zlm_client, "get_media_list", get_media_list)

    result = asyncio.run(service.get_status("stream_001"))

    assert result.online is False
    assert result.reader_count == 0
    assert result.raw == {"code": 0, "data": []}


def test_get_stream_status_raises_when_zlm_returns_error_code(monkeypatch) -> None:
    service = StreamStatusService()
    get_media_list = AsyncMock(side_effect=RuntimeError("unauthorized"))
    monkeypatch.setattr(zlm_client, "get_media_list", get_media_list)

    with pytest.raises(RuntimeError, match="unauthorized"):
        asyncio.run(service.get_status("stream_001"))


def test_get_stream_statuses_maps_multiple_video_sources(monkeypatch) -> None:
    service = StreamStatusService()
    get_media_list = AsyncMock(
        return_value={
            "code": 0,
            "data": [
                {
                    "app": "live",
                    "stream": "stream_001",
                    "schema": "rtmp",
                    "readerCount": 2,
                    "totalReaderCount": 5,
                }
            ],
        }
    )
    monkeypatch.setattr(zlm_client, "get_media_list", get_media_list)

    result = asyncio.run(service.get_statuses(["stream_001", "stream_002"]))

    assert result["stream_001"].online is True
    assert result["stream_001"].reader_count == 2
    assert result["stream_002"].online is False
    get_media_list.assert_awaited_once_with("live")


def test_zlm_client_get_media_list_adds_stream_only_when_present() -> None:
    client = ZlmClient()
    client._get = AsyncMock(return_value={"code": 0, "data": []})

    asyncio.run(client.get_media_list("live", "stream_001"))
    path, params = client._get.await_args.args
    assert path == "/index/api/getMediaList"
    assert params["app"] == "live"
    assert params["stream"] == "stream_001"

    client._get.reset_mock()
    asyncio.run(client.get_media_list("live"))
    _, params = client._get.await_args.args
    assert "stream" not in params
