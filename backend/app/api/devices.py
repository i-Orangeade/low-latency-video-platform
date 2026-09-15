from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate

router = APIRouter(prefix="/devices", tags=["devices"])


def get_device_or_404(device_id: int, db: Session) -> Device:
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
    return db.query(Device).order_by(Device.id.desc()).all()


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(device_in: DeviceCreate, db: Session = Depends(get_db)) -> Device:
    ensure_stream_id_available(device_in.stream_id, db)

    device = Device(**device_in.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)) -> Device:
    return get_device_or_404(device_id, db)


@router.put("/{device_id}", response_model=DeviceRead)
def update_device(device_id: int, device_in: DeviceUpdate, db: Session = Depends(get_db)) -> Device:
    device = get_device_or_404(device_id, db)

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
    device = get_device_or_404(device_id, db)

    db.delete(device)
    db.commit()
