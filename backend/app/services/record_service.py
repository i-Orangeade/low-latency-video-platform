from sqlalchemy.orm import Session

from app.models.record import Record
from app.schemas.record import RecordCreate


def create_record(db: Session, record_in: RecordCreate) -> Record:
    record = Record(**record_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
