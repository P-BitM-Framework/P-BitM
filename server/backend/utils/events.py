# utils/events.py
from database import SessionLocal
from models.victim_event import EventType, VictimEvent

def create_event(
    victim_id: str,
    campaign_id: str,
    event_type: EventType,
    title: str,
    description: str = None,
    metadata: dict = None
):
    """Create a new victim event"""
    db = SessionLocal()
    try:
        event = VictimEvent(
            victim_id=victim_id,
            campaign_id=campaign_id,
            event_type=event_type,
            title=title,
            description=description,
            payload=metadata or {},
        )

        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
