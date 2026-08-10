# admin-backend/utils/storage.py
import os
from pathlib import Path

from utils.artifact_files import safe_campaign_directory_name

STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "/storage"))
HOST_STORAGE_PATH = Path(os.getenv("HOST_STORAGE_PATH", "/path/to/host/storage"))


def setup_campaign_storage(campaign_name: str, campaign_id: str) -> Path:
    """Create and return the container-visible campaign storage path."""
    path = (
        STORAGE_PATH
        / "campaigns"
        / safe_campaign_directory_name(campaign_name, campaign_id)
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_host_campaign_storage_path(campaign_name: str, campaign_id: str) -> Path:
    """Return the matching host path without creating it in the container."""
    return (
        HOST_STORAGE_PATH
        / "campaigns"
        / safe_campaign_directory_name(campaign_name, campaign_id)
    )
