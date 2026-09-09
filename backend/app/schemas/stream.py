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
