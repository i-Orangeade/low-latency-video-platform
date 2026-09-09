import math
from typing import Any
from urllib.parse import parse_qs

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ZlmHookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    secret: str | None = Field(default=None, max_length=512)
    admin_params: str | dict[str, Any] | None = None
    stream: str | None = Field(default=None, max_length=100)
    app: str | None = Field(default=None, max_length=100)

    def supplied_secret(self) -> str | None:
        if self.secret is not None:
            return self.secret
        if isinstance(self.admin_params, dict):
            value = self.admin_params.get("secret")
            return value if isinstance(value, str) else None
        if isinstance(self.admin_params, str):
            values = parse_qs(self.admin_params.lstrip("?"), keep_blank_values=True)
            return values.get("secret", [None])[0]
        return None


class StreamChangedPayload(ZlmHookPayload):
    regist: bool


class RecordMp4Payload(ZlmHookPayload):
    file_path: str | None = Field(default=None, alias="filePath", max_length=500)
    file_name: str | None = Field(default=None, alias="fileName", max_length=255)
    time_len: int = Field(default=0, alias="timeLen", ge=0)
    file_size: int = Field(default=0, alias="fileSize", ge=0)

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("time_len", "file_size", mode="before")
    @classmethod
    def parse_non_negative_number(cls, value: Any) -> int:
        if value in (None, ""):
            return 0
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("must be numeric") from exc
        if not math.isfinite(number) or number < 0:
            raise ValueError("must be a non-negative finite number")
        return int(number)
