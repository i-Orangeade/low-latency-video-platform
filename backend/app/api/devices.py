# 视频源管理 API。
# 这一层只处理 HTTP 语义：校验后的请求、404/409 错误、数据库提交和响应状态码。
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate
from app.schemas.stream import DeviceStatusItem, DeviceStatusSummary
from app.services.zlm_service import zlm_service

router = APIRouter(prefix="/devices", tags=["devices"])


def get_device_or_404(device_id: int, db: Session) -> Device:
    # GET、PUT、DELETE 都必须先确认资源存在。
    # 将查询和 404 响应集中在这里，可以保证三个接口的错误信息完全一致。
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="device not found",
        )
    return device


def ensure_stream_id_available(
    stream_id: str,
    db: Session,
    exclude_device_id: int | None = None,
) -> None:
    # 创建时 exclude_device_id 为空，只要存在相同 stream_id 就视为冲突。
    # 更新时排除当前设备，允许请求继续携带设备自己的原 stream_id。
    query = db.query(Device).filter(Device.stream_id == stream_id)
    if exclude_device_id is not None:
        query = query.filter(Device.id != exclude_device_id)

    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="stream_id already exists",
        )


@router.get("", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db)) -> list[Device]:
    # 最新创建的视频源排在前面，便于前端直接展示最近添加的数据。
    return db.query(Device).order_by(Device.id.desc()).all()


@router.get("/status", response_model=DeviceStatusSummary)
async def get_device_status_summary(db: Session = Depends(get_db)) -> DeviceStatusSummary:
    # 先读取业务库中的视频源清单，再用一次 ZLM 聚合查询补充实时状态。
    devices = db.query(Device).order_by(Device.id.desc()).all()
    if not devices:
        return DeviceStatusSummary(total=0, online=0, offline=0, devices=[])

    try:
        statuses = await zlm_service.get_stream_statuses(
            [device.stream_id for device in devices]
        )
    except Exception as exc:
        # 聚合接口也依赖 ZLM；上游不可用时返回网关错误，而不是部分伪造结果。
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"failed to query ZLMediaKit: {exc}",
        ) from exc

    items = []
    for device in devices:
        stream_status = statuses[device.stream_id]
        items.append(
            DeviceStatusItem(
                id=device.id,
                name=device.name,
                stream_id=device.stream_id,
                **{key: value for key, value in stream_status.items() if key != "stream_id"},
            )
        )

    online_count = sum(item.online for item in items)
    return DeviceStatusSummary(
        total=len(items),
        online=online_count,
        offline=len(items) - online_count,
        devices=items,
    )


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(device_in: DeviceCreate, db: Session = Depends(get_db)) -> Device:
    # 先检查业务冲突，再执行插入。成功创建返回 201 和完整资源。
    ensure_stream_id_available(device_in.stream_id, db)

    device = Device(**device_in.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)) -> Device:
    # 单个资源查询不存在时统一返回 404。
    return get_device_or_404(device_id, db)


@router.put("/{device_id}", response_model=DeviceRead)
def update_device(device_id: int, device_in: DeviceUpdate, db: Session = Depends(get_db)) -> Device:
    # 更新流程依次处理：资源是否存在 -> stream_id 是否冲突 -> 写入字段并提交。
    device = get_device_or_404(device_id, db)

    # 只处理客户端实际提交的字段，未提交字段保持数据库中的原值。
    updates = device_in.model_dump(exclude_unset=True)
    if "stream_id" in updates:
        ensure_stream_id_available(
            updates["stream_id"],
            db,
            exclude_device_id=device_id,
        )

    for key, value in updates.items():
        setattr(device, key, value)

    db.commit()
    db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, db: Session = Depends(get_db)) -> None:
    # 删除成功返回 204，不返回响应体；资源不存在则返回 404。
    device = get_device_or_404(device_id, db)

    db.delete(device)
    db.commit()
