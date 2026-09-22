from fastapi import APIRouter, HTTPException, Query, status

from app.api.error_handling import zlm_http_exception
from app.dependencies import VideoSourceServiceDep
from app.models.video_source import VideoSource
from app.schemas.stream import VideoSourceStatusSummary
from app.schemas.video_source import (
    VideoSourceCreate,
    VideoSourcePage,
    VideoSourceRead,
    VideoSourceUpdate,
)
from app.services.video_source_service import (
    DuplicateStreamIdError,
    VideoSourceNotFoundError,
)
from app.services.zlm_errors import ZlmError

router = APIRouter(prefix="/video-sources", tags=["video-sources"])


@router.get("", response_model=VideoSourcePage)
def list_video_sources(
    video_source_service: VideoSourceServiceDep,
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    enabled: bool | None = None,
) -> VideoSourcePage:
    return video_source_service.list_page(
        page=page,
        page_size=page_size,
        query=q,
        enabled=enabled,
    )


@router.get("/status", response_model=VideoSourceStatusSummary)
async def get_video_source_status_summary(
    video_source_service: VideoSourceServiceDep,
) -> VideoSourceStatusSummary:
    try:
        return await video_source_service.get_status_summary()
    except ZlmError as exc:
        raise zlm_http_exception(exc) from exc


@router.post("", response_model=VideoSourceRead, status_code=status.HTTP_201_CREATED)
def create_video_source(
    source_in: VideoSourceCreate,
    video_source_service: VideoSourceServiceDep,
) -> VideoSource:
    try:
        return video_source_service.create(source_in)
    except DuplicateStreamIdError as exc:
        raise HTTPException(status_code=409, detail="stream_id already exists") from exc


@router.get("/{source_ref}", response_model=VideoSourceRead)
def get_video_source(
    source_ref: str,
    video_source_service: VideoSourceServiceDep,
) -> VideoSource:
    try:
        return video_source_service.get_by_reference(source_ref)
    except VideoSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="video source not found") from exc


@router.put("/{source_ref}", response_model=VideoSourceRead)
def update_video_source(
    source_ref: str,
    source_in: VideoSourceUpdate,
    video_source_service: VideoSourceServiceDep,
) -> VideoSource:
    try:
        return video_source_service.update_by_reference(source_ref, source_in)
    except VideoSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="video source not found") from exc
    except DuplicateStreamIdError as exc:
        raise HTTPException(status_code=409, detail="stream_id already exists") from exc


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_source(
    source_id: str,
    video_source_service: VideoSourceServiceDep,
) -> None:
    try:
        video_source_service.delete_by_reference(source_id)
    except VideoSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="video source not found") from exc
