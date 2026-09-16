from pydantic import BaseModel, Field


class PlayUrlResponse(BaseModel):
    stream_id: str
    protocol: str
    url: str


class StreamStatus(BaseModel):
    stream_id: str
    online: bool
    app: str
    schema_name: str | None = None
    origin_type: str | None = None
    reader_count: int = 0
    total_reader_count: int = 0
    tracks: list[dict] = Field(default_factory=list)


class StreamStatusResponse(StreamStatus):
    raw: dict = Field(default_factory=dict)


class VideoSourceStatusItem(StreamStatus):
    id: int
    name: str


class VideoSourceStatusSummary(BaseModel):
    total: int
    online: int
    offline: int
    video_sources: list[VideoSourceStatusItem] = Field(default_factory=list)
