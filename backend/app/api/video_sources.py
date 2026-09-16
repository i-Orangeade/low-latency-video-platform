from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.error_handling import zlm_http_exception
from app.database import get_db
from app.models.video_source import VideoSource
from app.schemas.stream import VideoSourceStatusItem, VideoSourceStatusSummary
from app.schemas.video_source import VideoSourceCreate, VideoSourceRead, VideoSourceUpdate
from app.services.stream_status_service import stream_status_service
from app.services.zlm_errors import ZlmError

router = APIRouter(prefix="/video-sources", tags=["video-sources"])


@router.get("", response_model=list[VideoSourceRead])
def list_video_sources(db: Session = Depends(get_db)) -> list[VideoSource]:
    return db.query(VideoSource).order_by(VideoSource.id.desc()).all()


@router.get("/status", response_model=VideoSourceStatusSummary)
async def get_video_source_status_summary(db: Session = Depends(get_db)) -> VideoSourceStatusSummary:
    video_sources = db.query(VideoSource).order_by(VideoSource.id.desc()).all()
    if not video_sources:
        return VideoSourceStatusSummary(total=0, online=0, offline=0, video_sources=[])

    stream_ids = [source.stream_id for source in video_sources]

    try:
        statuses = await stream_status_service.get_statuses(stream_ids)
    except ZlmError as exc:
        raise zlm_http_exception(exc) from exc

    items = [
        VideoSourceStatusItem(
            id=source.id,
            name=source.name,
            **statuses[source.stream_id].model_dump(),
        )
        for source in video_sources
    ]

    online = sum(1 for item in items if item.online)
    return VideoSourceStatusSummary(
        total=len(items),
        online=online,
        offline=len(items) - online,
        video_sources=items,
    )


@router.post("", response_model=VideoSourceRead, status_code=status.HTTP_201_CREATED)
def create_video_source(source_in: VideoSourceCreate, db: Session = Depends(get_db)) -> VideoSource:
    exists = db.query(VideoSource).filter(VideoSource.stream_id == source_in.stream_id).first()
    if exists:
        raise HTTPException(status_code=409, detail="stream_id already exists")

    source = VideoSource(**source_in.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/{source_id}", response_model=VideoSourceRead)
def get_video_source(source_id: int, db: Session = Depends(get_db)) -> VideoSource:
    source = db.get(VideoSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="video source not found")
    return source


@router.put("/{source_id}", response_model=VideoSourceRead)
def update_video_source(
    source_id: int,
    source_in: VideoSourceUpdate,
    db: Session = Depends(get_db),
) -> VideoSource:
    source = db.get(VideoSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="video source not found")

    updates = source_in.model_dump(exclude_unset=True)
    if "stream_id" in updates:
        exists = (
            db.query(VideoSource)
            .filter(VideoSource.stream_id == updates["stream_id"], VideoSource.id != source_id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="stream_id already exists")

    for key, value in updates.items():
        setattr(source, key, value)

    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_source(source_id: int, db: Session = Depends(get_db)) -> None:
    source = db.get(VideoSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="video source not found")

    db.delete(source)
    db.commit()
