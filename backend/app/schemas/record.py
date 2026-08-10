from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecordCreate(BaseModel):
    stream_id: str
    file_path: str
    file_name: str
    duration_seconds: int = 0
    file_size_bytes: int = 0
    started_at: datetime | None = None
    ended_at: datetime | None = None


class RecordRead(RecordCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
