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


class DeviceStatusItem(BaseModel):
    """一个已登记视频源及其当前媒体状态。"""

    id: int
    name: str
    stream_id: str
    online: bool
    app: str
    schema_name: str | None = None
    origin_type: str | None = None
    reader_count: int = 0
    total_reader_count: int = 0
    tracks: list[dict] = Field(default_factory=list)


class DeviceStatusSummary(BaseModel):
    """所有已登记视频源的状态统计和明细。"""

    total: int
    online: int
    offline: int
    devices: list[DeviceStatusItem] = Field(default_factory=list)
