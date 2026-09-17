from sqlalchemy.orm import Session

from app.models.video_source import VideoSource
from app.schemas.stream import VideoSourceStatusItem, VideoSourceStatusSummary
from app.schemas.video_source import VideoSourceCreate, VideoSourceUpdate
from app.services.stream_status_service import StreamStatusService


class VideoSourceNotFoundError(LookupError):
    """Raised when a requested video source does not exist."""


class DuplicateStreamIdError(ValueError):
    """Raised when a stream ID is already registered by another source."""


class VideoSourceService:
    """Owns video-source persistence and status aggregation use cases."""

    def __init__(self, db: Session, stream_status_service: StreamStatusService) -> None:
        self._db = db
        self._stream_status_service = stream_status_service

    def list(self) -> list[VideoSource]:
        return self._db.query(VideoSource).order_by(VideoSource.id.desc()).all()

    async def get_status_summary(self) -> VideoSourceStatusSummary:
        video_sources = self.list()
        if not video_sources:
            return VideoSourceStatusSummary(total=0, online=0, offline=0, video_sources=[])

        stream_ids = [source.stream_id for source in video_sources]
        statuses = await self._stream_status_service.get_statuses(stream_ids)
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

    def create(self, source_in: VideoSourceCreate) -> VideoSource:
        self._ensure_stream_id_available(source_in.stream_id)
        source = VideoSource(**source_in.model_dump())
        self._db.add(source)
        self._db.commit()
        self._db.refresh(source)
        return source

    def get(self, source_id: int) -> VideoSource:
        source = self._db.get(VideoSource, source_id)
        if not source:
            raise VideoSourceNotFoundError
        return source

    def update(self, source_id: int, source_in: VideoSourceUpdate) -> VideoSource:
        source = self.get(source_id)
        updates = source_in.model_dump(exclude_unset=True)
        if "stream_id" in updates:
            self._ensure_stream_id_available(updates["stream_id"], exclude_id=source_id)

        for key, value in updates.items():
            setattr(source, key, value)

        self._db.commit()
        self._db.refresh(source)
        return source

    def delete(self, source_id: int) -> None:
        source = self.get(source_id)
        self._db.delete(source)
        self._db.commit()

    def _ensure_stream_id_available(self, stream_id: str, exclude_id: int | None = None) -> None:
        query = self._db.query(VideoSource).filter(VideoSource.stream_id == stream_id)
        if exclude_id is not None:
            query = query.filter(VideoSource.id != exclude_id)
        if query.first():
            raise DuplicateStreamIdError
