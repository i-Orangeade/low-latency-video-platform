from pydantic import BaseModel, ConfigDict


class DeviceBase(BaseModel):
    name: str
    stream_id: str


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: str | None = None
    stream_id: str | None = None


class DeviceRead(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
