from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeviceBase(BaseModel):
    name: str
    stream_id: str
    location: str | None = None
    description: str | None = None
    enabled: bool = True


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: str | None = None
    stream_id: str | None = None
    location: str | None = None
    description: str | None = None
    enabled: bool | None = None


class DeviceRead(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_online: bool
    created_at: datetime
    updated_at: datetime
