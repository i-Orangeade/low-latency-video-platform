# API 请求和响应模型。
# Pydantic 在路由函数执行前完成字段类型、长度和格式校验，非法请求不会进入数据库逻辑。
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# stream_id 会进入 ZLM 的 URL 路径。
# 只允许字母、数字、下划线和连字符，避免斜杠、空格或特殊字符改变 URL 结构。
STREAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def strip_string(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def validate_stream_id(value: str | None) -> str | None:
    if value is not None and not STREAM_ID_PATTERN.fullmatch(value):
        raise ValueError("stream_id may only contain letters, numbers, underscore, and hyphen")
    return value


class DeviceBase(BaseModel):
    # 创建视频源必须同时提供 name 和 stream_id。
    name: str = Field(min_length=1, max_length=100)
    stream_id: str = Field(min_length=1, max_length=100)

    @field_validator("name", "stream_id", mode="before")
    @classmethod
    def strip_text_fields(cls, value: Any) -> Any:
        # 先去除首尾空白，再执行长度和 stream_id 字符校验。
        return strip_string(value)

    @field_validator("stream_id")
    @classmethod
    def stream_id_has_supported_characters(cls, value: str) -> str:
        return validate_stream_id(value) or value


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    # 更新模型与创建模型不同：字段允许省略，以支持只修改名称或只修改 stream_id。
    # 但显式传入 null 会被下面的校验器拒绝，避免把 None 写入数据库非空列。
    name: str | None = Field(default=None, min_length=1, max_length=100)
    stream_id: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("name", "stream_id", mode="before")
    @classmethod
    def strip_text_fields(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field may not be null")
        return strip_string(value)

    @field_validator("stream_id")
    @classmethod
    def stream_id_has_supported_characters(cls, value: str | None) -> str | None:
        return validate_stream_id(value)


class DeviceRead(DeviceBase):
    # 响应模型除业务字段外还包含数据库生成的 id。
    # from_attributes=True 允许 Pydantic 直接从 SQLAlchemy Device 对象读取属性。
    model_config = ConfigDict(from_attributes=True)

    id: int
