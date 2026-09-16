import asyncio

import httpx
import pytest

from app.services.zlm_client import ZlmClient
from app.services.zlm_errors import ZlmApiError, ZlmConnectionError, ZlmHttpError, ZlmResponseError


class FakeResponse:
    def __init__(
        self,
        payload=None,
        status_code: int = 200,
        json_error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error
        self.request = httpx.Request("GET", "http://zlm.local/index/api/test")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = httpx.Response(self.status_code, request=self.request)
            raise httpx.HTTPStatusError("HTTP error", request=self.request, response=response)

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeAsyncClient:
    response: FakeResponse | None = None
    request_error: httpx.RequestError | None = None
    last_params: dict | None = None

    def __init__(self, timeout: float) -> None:
        self.__class__.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url: str, params: dict):
        self.__class__.last_params = params
        if self.__class__.request_error:
            raise self.__class__.request_error
        return self.__class__.response


@pytest.fixture(autouse=True)
def reset_fake_client(monkeypatch):
    FakeAsyncClient.response = None
    FakeAsyncClient.request_error = None
    FakeAsyncClient.last_params = None
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)


def test_zlm_client_returns_payload() -> None:
    FakeAsyncClient.response = FakeResponse({"code": 0, "data": []})

    result = asyncio.run(ZlmClient().get_media_list("live", "stream_001"))

    assert result == {"code": 0, "data": []}
    assert FakeAsyncClient.last_params["stream"] == "stream_001"


def test_zlm_client_maps_connection_errors() -> None:
    request = httpx.Request("GET", "http://zlm.local/index/api/getMediaList")
    FakeAsyncClient.request_error = httpx.ConnectError("connect failed", request=request)

    with pytest.raises(ZlmConnectionError, match="connect failed"):
        asyncio.run(ZlmClient().get_media_list("live"))


def test_zlm_client_maps_http_errors() -> None:
    FakeAsyncClient.response = FakeResponse({"code": 0}, status_code=500)

    with pytest.raises(ZlmHttpError, match="HTTP 500"):
        asyncio.run(ZlmClient().get_media_list("live"))


def test_zlm_client_maps_api_errors() -> None:
    FakeAsyncClient.response = FakeResponse({"code": -1, "msg": "bad secret"})

    with pytest.raises(ZlmApiError, match="bad secret"):
        asyncio.run(ZlmClient().get_media_list("live"))


def test_zlm_client_maps_invalid_json() -> None:
    FakeAsyncClient.response = FakeResponse(json_error=ValueError("invalid json"))

    with pytest.raises(ZlmResponseError, match="invalid JSON"):
        asyncio.run(ZlmClient().get_media_list("live"))


def test_zlm_client_maps_non_object_payload() -> None:
    FakeAsyncClient.response = FakeResponse([{"code": 0}])

    with pytest.raises(ZlmResponseError, match="non-object"):
        asyncio.run(ZlmClient().get_media_list("live"))
