import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


STREAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def strip_string(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def validate_stream_id(value: str | None) -> str | None:
    if value is not None and not STREAM_ID_PATTERN.fullmatch(value):
        raise ValueError("stream_id may only contain letters, numbers, underscore, and hyphen")
    return value


class VideoSourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    stream_id: str = Field(min_length=1, max_length=100)
    enabled: bool = True

    @field_validator("name", "stream_id", mode="before")
    @classmethod
    def strip_text_fields(cls, value: Any) -> Any:
        return strip_string(value)

    @field_validator("stream_id")
    @classmethod
    def stream_id_has_supported_characters(cls, value: str) -> str:
        return validate_stream_id(value) or value


class VideoSourceCreate(VideoSourceBase):
    pass


class VideoSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    stream_id: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None

    @field_validator("name", "stream_id", mode="before")
    @classmethod
    def strip_text_fields(cls, value: Any) -> Any:
        return strip_string(value)

    @field_validator("stream_id")
    @classmethod
    def stream_id_has_supported_characters(cls, value: str | None) -> str | None:
        return validate_stream_id(value)


class VideoSourceRead(VideoSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
