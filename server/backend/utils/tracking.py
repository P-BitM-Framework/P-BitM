# admin-backend/utils/tracking.py

import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import Victim, VictimEvent, EventType, VictimStatus

INTERACTIVE_IP_METADATA_KEY = "interactive_ip_address"

def generate_tracking_id() -> str:
    """Generate unique tracking token for victim."""
    return str(uuid.uuid4())


def create_tracking_event(
    db: Session,
    victim: Victim,
    event_type: EventType,
    title: str,
    description: str = None,
    url: str = None,
    hostname: str = None,
    payload: dict = None
) -> VictimEvent:
    """
    Create and save a tracking event.

    Args:
        db: Database session
        victim: Victim instance
        event_type: Type of event (from EventType enum)
        title: Event title
        description: Event description (optional)
        url: URL associated with event (optional)
        hostname: Hostname (optional)
        payload: Additional data as dict (optional)

    Returns:
        VictimEvent instance
    """
    event = VictimEvent(
        id=str(uuid.uuid4()),
        victim_id=victim.id,
        campaign_id=victim.campaign_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        title=title,
        description=description,
        url=url,
        hostname=hostname,
        payload=payload,
    )

    db.add(event)
    return event


def update_victim_opened(
    db: Session,
    victim: Victim,
    ip_address: str = None,
    user_agent: str = None
) -> bool:
    """
    Update victim when email is opened.

    Args:
        db: Database session
        victim: Victim instance
        ip_address: Client IP address (optional)
        user_agent: Client user agent (optional)

    Returns:
        bool: True if this is the first open (status changed)
    """
    victim.email_opened_at = datetime.now(timezone.utc)
    victim.status = VictimStatus.email_opened

    # Update campaign stats
    if victim.campaign:
        victim.campaign.emails_opened += 1

    # Create tracking event
    ua_info = parse_user_agent(user_agent) if user_agent else {}
    create_tracking_event(
        db=db,
        victim=victim,
        event_type=EventType.EMAIL_OPENED,
        title="📧 Email Opened",
        description=f"Email opened from {ua_info.get('device', 'Unknown')} ({ua_info.get('browser', 'Unknown')} on {ua_info.get('os', 'Unknown')})",
        payload={
            'ip_address': ip_address,
            'user_agent': user_agent,
            'device_info': ua_info
        }
    )

    # Update last seen and metadata
    if not victim.first_seen:
        victim.first_seen = datetime.now(timezone.utc)
        victim.last_seen = victim.first_seen
    else:
        victim.last_seen = datetime.now(timezone.utc)

    if ip_address and not victim.ip_address:
        victim.ip_address = ip_address

    if user_agent and not victim.user_agent:
        victim.user_agent = user_agent

    if ua_info and not victim.browser:
        victim.browser = ua_info.get('browser', 'Unknown')

    if ua_info and not victim.os:
        victim.os = ua_info.get('os', 'Unknown')

    db.commit()
    return True


def update_victim_clicked(
    db: Session,
    victim: Victim,
    ip_address: str = None,
    user_agent: str = None
) -> bool:
    """
    Update victim when link is clicked.

    Args:
        db: Database session
        victim: Victim instance
        ip_address: Client IP address (optional)
        user_agent: Client user agent (optional)

    Returns:
        bool: True if this is the first click (status changed)
    """
    first_click = False
    ua_info = parse_user_agent(user_agent) if user_agent else {}

    if not victim.email_link_clicked_at:
        victim.email_link_clicked_at = datetime.now(timezone.utc)
        victim.status = VictimStatus.email_link_clicked
        first_click = True

        # Update campaign stats
        if victim.campaign:
            victim.campaign.links_clicked += 1

        # Create tracking event
        create_tracking_event(
            db=db,
            victim=victim,
            event_type=EventType.EMAIL_LINK_CLICKED,
            title="🔗 Link Clicked",
            description=f"Link clicked from {ua_info.get('device', 'Unknown')} ({ua_info.get('browser', 'Unknown')} on {ua_info.get('os', 'Unknown')})",
            payload={
                'ip_address': ip_address,
                'user_agent': user_agent,
                'device_info': ua_info
            }
        )

    # Update last seen and browser info
    victim.last_seen = datetime.now(timezone.utc)

    metadata = victim.extra_metadata or {}
    if ip_address and not metadata.get(INTERACTIVE_IP_METADATA_KEY):
        victim.ip_address = ip_address

    if user_agent and not metadata.get(INTERACTIVE_IP_METADATA_KEY):
        victim.user_agent = user_agent

    if ua_info and not victim.browser:
        victim.browser = ua_info.get('browser', 'Unknown')

    if ua_info and not victim.os:
        victim.os = ua_info.get('os', 'Unknown')

    db.commit()
    return first_click


def update_victim_submitted(
    db: Session,
    victim: Victim,
    submitted_data: dict = None
) -> bool:
    """
    Update victim when data is submitted.

    Args:
        db: Database session
        victim: Victim instance
        submitted_data: Submitted form data (optional)

    Returns:
        bool: True if this is the first submission (status changed)
    """
    first_submit = False

    if not victim.data_submitted_at:
        victim.data_submitted_at = datetime.now(timezone.utc)
        victim.status = VictimStatus.data_submitted
        first_submit = True

        # Update campaign stats
        if victim.campaign:
            victim.campaign.data_submitted += 1

        # Create tracking event
        create_tracking_event(
            db=db,
            victim=victim,
            event_type=EventType.FORM_SUBMISSION,
            title="📝 Data Submitted",
            description="Victim submitted form data",
            payload=submitted_data
        )

    # Save submitted data
    if submitted_data:
        victim.submitted_data = submitted_data

    victim.last_seen = datetime.now(timezone.utc)

    db.commit()
    return first_submit


def parse_user_agent(user_agent: str) -> dict:
    """
    Parse user agent string to extract browser and OS info.

    Args:
        user_agent: User agent string

    Returns:
        dict with keys: browser, os, device
    """
    if not user_agent:
        return {'browser': 'Unknown', 'os': 'Unknown', 'device': 'Unknown'}

    ua_lower = user_agent.lower()

    # Detect browser
    if 'firefox' in ua_lower:
        browser = 'Firefox'
    elif 'chrome' in ua_lower and 'edg' not in ua_lower:
        browser = 'Chrome'
    elif 'safari' in ua_lower and 'chrome' not in ua_lower:
        browser = 'Safari'
    elif 'edg' in ua_lower:
        browser = 'Edge'
    else:
        browser = 'Unknown'

    # Detect OS
    if 'windows' in ua_lower:
        os_name = 'Windows'
    elif 'mac' in ua_lower or 'darwin' in ua_lower:
        os_name = 'macOS'
    elif 'linux' in ua_lower:
        os_name = 'Linux'
    elif 'android' in ua_lower:
        os_name = 'Android'
    elif 'iphone' in ua_lower or 'ipad' in ua_lower:
        os_name = 'iOS'
    else:
        os_name = 'Unknown'

    # Detect device
    if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
        device = 'Mobile'
    elif 'tablet' in ua_lower or 'ipad' in ua_lower:
        device = 'Tablet'
    else:
        device = 'Desktop'

    return {
        'browser': browser,
        'os': os_name,
        'device': device
    }
