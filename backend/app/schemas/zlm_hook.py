from pydantic import BaseModel, ConfigDict, Field


class OnPublishPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    app: str | None = Field(default=None, max_length=100)
    stream: str | None = Field(default=None, max_length=100)


class ZlmHookResponse(BaseModel):
    code: int
    msg: str
