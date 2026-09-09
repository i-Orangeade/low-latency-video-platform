from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.record import Record
from app.schemas.record import RecordCreate


def create_record(db: Session, record_in: RecordCreate) -> Record:
    record = Record(**record_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_record_once(db: Session, record_in: RecordCreate) -> Record:
    existing = db.query(Record).filter(Record.file_path == record_in.file_path).first()
    if existing:
        return existing
    try:
        return create_record(db, record_in)
    except IntegrityError:
        db.rollback()
        existing = db.query(Record).filter(Record.file_path == record_in.file_path).first()
        if existing:
            return existing
        raise
