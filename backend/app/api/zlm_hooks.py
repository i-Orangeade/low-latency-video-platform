import hmac

from fastapi import APIRouter, Request

from app.config import settings
from app.dependencies import DbSession
from app.models.video_source import VideoSource
from app.schemas.zlm_hook import OnPublishPayload, ZlmHookResponse

router = APIRouter(prefix="/zlm/hooks", tags=["zlm-hooks"])


def _authorized(token: str | None) -> bool:
    expected = settings.zlm_hook_secret
    if not token or len(token) > 512 or not expected:
        return False
    return hmac.compare_digest(
        token.encode("utf-8"),
        expected.encode("utf-8"),
    )


def _rejected(message: str) -> ZlmHookResponse:
    return ZlmHookResponse(code=-1, msg=message)


@router.post("/on_publish", response_model=ZlmHookResponse)
def on_publish(
    payload: OnPublishPayload,
    request: Request,
    db: DbSession,
) -> ZlmHookResponse:
    hook_token = request.query_params.get("token")
    # Uvicorn access logs include the query string; remove the secret after
    # authentication so it never reaches the access log.
    request.scope["query_string"] = b""
    if not _authorized(hook_token):
        return _rejected("unauthorized hook")
    if payload.app != settings.default_app or not payload.stream:
        return _rejected("unknown or disabled stream")

    source = (
        db.query(VideoSource)
        .filter(
            VideoSource.stream_id == payload.stream,
            VideoSource.enabled.is_(True),
        )
        .first()
    )
    if not source:
        return _rejected("unknown or disabled stream")
    return ZlmHookResponse(code=0, msg="success")
