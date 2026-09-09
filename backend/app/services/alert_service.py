from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.schemas.alert import AlertCreate


def create_alert(db: Session, alert_in: AlertCreate) -> Alert:
    alert = Alert(**alert_in.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def create_offline_alert_once(db: Session, stream_id: str) -> Alert:
    existing = (
        db.query(Alert)
        .filter(
            Alert.stream_id == stream_id,
            Alert.category == "stream_offline",
            Alert.is_read.is_(False),
        )
        .first()
    )
    if existing:
        return existing
    return create_alert(
        db,
        AlertCreate(
            stream_id=stream_id,
            level="warning",
            category="stream_offline",
            message=f"Stream {stream_id} is offline.",
        ),
    )


def resolve_offline_alerts(db: Session, stream_id: str) -> None:
    alerts = (
        db.query(Alert)
        .filter(
            Alert.stream_id == stream_id,
            Alert.category == "stream_offline",
            Alert.is_read.is_(False),
        )
        .all()
    )
    if not alerts:
        return
    for alert in alerts:
        alert.is_read = True
    db.commit()
