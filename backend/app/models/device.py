# 数据库 ORM 模型。
# Device 表示平台中登记的一个逻辑视频源，它保存名称和 ZLMediaKit 使用的 stream_id。
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # stream_id 会出现在 RTMP 推流路径和 HTTP-FLV 播放路径中。
    # 同一个 stream_id 如果重复，多个视频源会映射到同一路媒体流，因此数据库强制唯一。
    stream_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
