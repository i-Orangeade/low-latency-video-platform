from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VideoSource(Base):
    __tablename__ = "video_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    stream_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
