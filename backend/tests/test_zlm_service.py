import asyncio
from unittest.mock import AsyncMock

from app.services.zlm_service import ZlmService


def test_stream_qos_maps_custom_zlm_response() -> None:
    service = ZlmService()
    service._get = AsyncMock(
        return_value={
            "code": 0,
            "data": {
                "probeMs": 2000,
                "bitrateKbps": 1850.5,
                "videoFps": 24.5,
                "videoFrameCount": 49,
                "audioFrameCount": 94,
                "keyFrameCount": 2,
                "averageGopMs": 1000.0,
                "firstFrameDelayMs": 17,
                "timestampRollbackCount": 0,
                "readerCount": 1,
                "totalReaderCount": 2,
                "currentBytesSpeed": 231312,
                "aliveSecond": 42,
            },
        }
    )

    result = asyncio.run(service.get_stream_qos("drone_001", 2000))

    assert result["stream_id"] == "drone_001"
    assert result["bitrate_kbps"] == 1850.5
    assert result["video_fps"] == 24.5
    assert result["average_gop_ms"] == 1000.0
    assert result["first_frame_delay_ms"] == 17
    service._get.assert_awaited_once()
