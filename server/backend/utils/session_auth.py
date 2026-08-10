from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from models.user_session import UserSession


logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "__Host-pbitm_session"
SESSION_TTL_HOURS = int(os.getenv("ADMIN_SESSION_TTL_HOURS", "12"))
SESSION_MAX_AGE_SECONDS = SESSION_TTL_HOURS * 60 * 60
MAX_SESSIONS_PER_USER = int(os.getenv("ADMIN_MAX_SESSIONS_PER_USER", "5"))

if SESSION_TTL_HOURS <= 0:
    raise RuntimeError("ADMIN_SESSION_TTL_HOURS must be greater than zero")
if MAX_SESSIONS_PER_USER <= 0:
    raise RuntimeError("ADMIN_MAX_SESSIONS_PER_USER must be greater than zero")


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )


def create_user_session(
    db: Session,
    *,
    user_id: str,
    request: Request,
) -> tuple[str, str, UserSession]:
    now = datetime.now(timezone.utc)
    db.query(UserSession).filter(UserSession.expires_at <= now).delete(
        synchronize_session=False
    )

    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id)
        .order_by(UserSession.created_at.desc())
        .all()
    )
    for old_session in sessions[MAX_SESSIONS_PER_USER - 1 :]:
        db.delete(old_session)

    token = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    session = UserSession(
        token_hash=hash_secret(token),
        csrf_hash=hash_secret(csrf_token),
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(hours=SESSION_TTL_HOURS),
        last_seen_at=now,
        user_agent=(request.headers.get("user-agent") or "")[:512] or None,
        ip_address=request.client.host[:64] if request.client else None,
    )
    db.add(session)
    return token, csrf_token, session


def resolve_user_session(request: Request, db: Session) -> UserSession:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token or len(raw_token) > 256:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    session = db.query(UserSession).filter(
        UserSession.token_hash == hash_secret(raw_token)
    ).first()
    if session is None:
        # A cookie was presented but matches no known session: either a
        # stale/already-cleaned-up session or a forged token. Distinct from
        # "no cookie at all", which every logged-out page load produces and
        # isn't worth logging.
        logger.warning(
            "Rejected session cookie that does not match any known session"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    now = datetime.now(timezone.utc)
    if session.expires_at <= now:
        db.delete(session)
        db.commit()
        logger.warning(
            "Rejected expired session for user %s", session.user_id
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        csrf_token = request.headers.get("x-csrf-token")
        if not csrf_token or not hmac.compare_digest(
            hash_secret(csrf_token),
            session.csrf_hash,
        ):
            logger.warning(
                "Rejected %s request for user %s: invalid or missing CSRF token",
                request.method,
                session.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing CSRF token",
            )

    request.state.user_session = session
    return session


def revoke_current_session(request: Request, db: Session) -> None:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        return
    db.query(UserSession).filter(
        UserSession.token_hash == hash_secret(raw_token)
    ).delete(synchronize_session=False)


def rotate_csrf_token(session: UserSession) -> str:
    csrf_token = secrets.token_urlsafe(32)
    session.csrf_hash = hash_secret(csrf_token)
    return csrf_token


def revoke_user_sessions(db: Session, user_id: str) -> None:
    db.query(UserSession).filter(UserSession.user_id == user_id).delete(
        synchronize_session=False
    )
