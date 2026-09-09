from pydantic import BaseModel, Field


class PlayUrlResponse(BaseModel):
    stream_id: str
    protocol: str
    url: str


class StreamStatusResponse(BaseModel):
    stream_id: str
    online: bool
    app: str
    schema_name: str | None = None
    origin_type: str | None = None
    reader_count: int = 0
    total_reader_count: int = 0
    tracks: list[dict] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class StreamQosResponse(BaseModel):
    stream_id: str
    probe_ms: int
    bitrate_kbps: float
    video_fps: float
    video_frame_count: int
    audio_frame_count: int
    key_frame_count: int
    average_gop_ms: float | None = None
    first_frame_delay_ms: int | None = None
    timestamp_rollback_count: int
    reader_count: int
    total_reader_count: int
    current_bytes_speed: int
    alive_second: int
