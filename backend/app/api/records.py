from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.record import Record
from app.schemas.record import RecordRead

router = APIRouter(prefix="/records", tags=["records"])


@router.get("", response_model=list[RecordRead])
def list_records(db: Session = Depends(get_db)) -> list[Record]:
    return db.query(Record).order_by(Record.id.desc()).all()


@router.get("/{record_id}", response_model=RecordRead)
def get_record(record_id: int, db: Session = Depends(get_db)) -> Record:
    record = db.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="record not found")
    return record
