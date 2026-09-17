from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.stream_status_service import StreamStatusService
from app.services.video_source_service import VideoSourceService
from app.services.zlm_client import ZlmClient, zlm_client


DbSession = Annotated[Session, Depends(get_db)]


def get_zlm_client() -> ZlmClient:
    return zlm_client


ZlmClientDep = Annotated[ZlmClient, Depends(get_zlm_client)]


def get_stream_status_service(zlm_client: ZlmClientDep) -> StreamStatusService:
    return StreamStatusService(zlm_client)


StreamStatusServiceDep = Annotated[StreamStatusService, Depends(get_stream_status_service)]


def get_video_source_service(
    db: DbSession,
    stream_status_service: StreamStatusServiceDep,
) -> VideoSourceService:
    return VideoSourceService(db, stream_status_service)


VideoSourceServiceDep = Annotated[VideoSourceService, Depends(get_video_source_service)]
