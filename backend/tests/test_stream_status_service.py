import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.stream_status_service import StreamStatusService
from app.services.zlm_errors import ZlmApiError, ZlmResponseError
from app.services.zlm_client import ZlmClient


def _zlm_client(**methods):
    return SimpleNamespace(**methods)


def test_get_stream_status_online_maps_media_list() -> None:
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
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

    result = asyncio.run(service.get_status("stream_001"))

    assert result.stream_id == "stream_001"
    assert result.online is True
    assert result.schema_name == "rtmp"
    assert result.origin_type == "rtmp_push"
    assert result.reader_count == 1
    assert result.raw["schema"] == "rtmp"
    get_media_list.assert_awaited_once_with("live", "stream_001")


def test_get_stream_status_offline_when_media_list_empty() -> None:
    get_media_list = AsyncMock(return_value={"code": 0, "data": []})
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

    result = asyncio.run(service.get_status("stream_001"))

    assert result.online is False
    assert result.reader_count == 0
    assert result.raw == {"code": 0, "data": []}


def test_get_stream_status_raises_when_zlm_returns_error_code() -> None:
    get_media_list = AsyncMock(side_effect=ZlmApiError(-1, "unauthorized"))
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

    with pytest.raises(ZlmApiError, match="unauthorized"):
        asyncio.run(service.get_status("stream_001"))


def test_get_stream_status_ignores_mismatched_stream() -> None:
    get_media_list = AsyncMock(
        return_value={
            "code": 0,
            "data": [{"app": "live", "stream": "other_stream", "schema": "rtmp"}],
        }
    )
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

    result = asyncio.run(service.get_status("stream_001"))

    assert result.online is False
    assert result.raw["data"][0]["stream"] == "other_stream"


def test_get_stream_status_finds_target_stream_after_other_records() -> None:
    get_media_list = AsyncMock(
        return_value={
            "code": 0,
            "data": [
                {"app": "live", "stream": "other_stream", "schema": "rtmp"},
                {
                    "app": "live",
                    "stream": "stream_001",
                    "schema": "rtmp",
                    "readerCount": 2,
                },
            ],
        }
    )
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

    result = asyncio.run(service.get_status("stream_001"))

    assert result.online is True
    assert result.reader_count == 2
    assert result.raw["stream"] == "stream_001"


def test_get_stream_status_does_not_use_record_without_stream_id() -> None:
    get_media_list = AsyncMock(
        return_value={
            "code": 0,
            "data": [{"app": "live", "schema": "rtmp", "readerCount": 9}],
        }
    )
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

    result = asyncio.run(service.get_status("stream_001"))

    assert result.online is False
    assert result.raw["data"][0]["readerCount"] == 9


def test_get_stream_status_rejects_malformed_media_list() -> None:
    get_media_list = AsyncMock(return_value={"code": 0, "data": {"unexpected": True}})
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

    with pytest.raises(ZlmResponseError, match="data"):
        asyncio.run(service.get_status("stream_001"))


def test_get_stream_statuses_returns_empty_without_querying_zlm() -> None:
    get_media_list = AsyncMock()
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

    result = asyncio.run(service.get_statuses([]))

    assert result == {}
    get_media_list.assert_not_awaited()


def test_get_stream_statuses_maps_multiple_video_sources() -> None:
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
    service = StreamStatusService(_zlm_client(get_media_list=get_media_list))

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
