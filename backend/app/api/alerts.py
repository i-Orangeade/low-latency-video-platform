from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertRead
from app.services.alert_service import create_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(db: Session = Depends(get_db)) -> list[Alert]:
    return db.query(Alert).order_by(Alert.id.desc()).all()


@router.post("/test", response_model=AlertRead)
def create_test_alert(db: Session = Depends(get_db)) -> Alert:
    return create_alert(
        db,
        AlertCreate(
            stream_id="drone_001",
            level="warning",
            category="stream_test",
            message="This is a test alert for the drone video stream.",
        ),
    )


@router.put("/{alert_id}/read", response_model=AlertRead)
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="alert not found")

    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert
