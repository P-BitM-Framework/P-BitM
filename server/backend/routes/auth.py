# admin-backend/routes/auth.py
import os
import hmac
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone
import logging
from typing import Optional

from database import get_db
from models.user import User
from utils.auth import verify_password
from utils.client_ip import get_dashboard_client_ip
from utils.permissions import (
    VALID_USER_ROLES,
    can_access_campaign,
    can_manage_resources,
)
from utils.internal_auth import derive_campaign_api_key
from utils.login_rate_limiter import LoginRateLimiter
from utils.session_auth import (
    clear_session_cookie,
    create_user_session,
    resolve_user_session,
    revoke_current_session,
    rotate_csrf_token,
    set_session_cookie,
)


INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]

logger = logging.getLogger(__name__)

router = APIRouter()
login_rate_limiter = LoginRateLimiter()


def _disable_auth_response_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    user: dict
    csrf_token: str


async def get_current_user_from_session(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    session = resolve_user_session(request, db)
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        logger.warning(
            "Rejected session for user %s: user not found or deactivated",
            session.user_id,
        )
        db.delete(session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    if user.role not in VALID_USER_ROLES:
        logger.warning(
            "Rejected session for user %s: unsupported role '%s'",
            user.id,
            user.role,
        )
        db.delete(session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is no longer supported",
        )
    return user


async def verify_campaign_internal_key(
    campaign_id: str,
    x_internal_api_key: Optional[str] = Header(None),
):
    """Require the credential derived specifically for the path campaign."""
    expected_key = derive_campaign_api_key(INTERNAL_API_KEY, campaign_id)
    if x_internal_api_key and hmac.compare_digest(x_internal_api_key, expected_key):
        return True
    logger.warning(
        "Rejected internal campaign request for %s: invalid or missing credentials",
        campaign_id,
    )
    raise HTTPException(403, "Invalid or missing campaign credentials")


async def verify_tracking_internal_key(
    request: Request,
    x_internal_api_key: Optional[str] = Header(None),
):
    """Scope tracking callbacks using the campaign_id carried in their JSON body."""
    try:
        data = await request.json()
        campaign_id = data.get("campaign_id")
    except Exception:
        campaign_id = None

    if not campaign_id:
        logger.warning(
            "Rejected tracking callback: missing or unparseable campaign_id in body"
        )
        raise HTTPException(403, "Invalid or missing campaign credentials")

    expected_key = derive_campaign_api_key(INTERNAL_API_KEY, campaign_id)
    if x_internal_api_key and hmac.compare_digest(x_internal_api_key, expected_key):
        return True
    logger.warning(
        "Rejected tracking callback for %s: invalid or missing credentials",
        campaign_id,
    )
    raise HTTPException(403, "Invalid or missing campaign credentials")

@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate a user and establish a revocable server-side session."""

    client_ip = get_dashboard_client_ip(request)

    if not await login_rate_limiter.record_attempt_if_allowed(
        ip=client_ip,
        username=data.username,
    ):
        logger.warning(
            "Login rate-limited for user '%s' from %s",
            data.username,
            client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(login_rate_limiter.window_seconds)},
        )

    # Find user
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password):
        logger.warning(
            "Failed login for user '%s' from %s: invalid username or password",
            data.username,
            client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Check if active
    if not user.is_active:
        logger.warning(
            "Failed login for user '%s' from %s: account disabled",
            data.username,
            client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    if user.role not in VALID_USER_ROLES:
        logger.warning(
            "Failed login for user '%s' from %s: unsupported role '%s'",
            data.username,
            client_ip,
            user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is no longer supported",
        )

    await login_rate_limiter.record_success(ip=client_ip, username=data.username)

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    revoke_current_session(request, db)
    session_token, csrf_token, _ = create_user_session(
        db,
        user_id=user.id,
        request=request,
    )
    db.commit()
    set_session_cookie(response, session_token)
    _disable_auth_response_caching(response)

    return {
        "user": user.to_dict(),
        "csrf_token": csrf_token,
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user_from_session),
):
    """Revoke the current session and remove its browser cookie."""
    revoke_current_session(request, db)
    db.commit()
    clear_session_cookie(response)
    _disable_auth_response_caching(response)
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session),
):
    """Get the current user and rotate the browser-readable CSRF token."""
    csrf_token = rotate_csrf_token(request.state.user_session)
    db.commit()
    _disable_auth_response_caching(response)
    return {
        "user": current_user.to_dict(),
        "csrf_token": csrf_token,
    }


# ========================================
# DEPENDENCIES
# ========================================

async def require_admin(
    current_user: User = Depends(get_current_user_from_session)
) -> User:
    """
    Dependency to require admin role
    Usage: current_user = Depends(require_admin)
    """
    if not current_user.is_admin():
        logger.warning(
            "Rejected admin-only request from user %s (role '%s')",
            current_user.id,
            current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def require_operator(
    current_user: User = Depends(get_current_user_from_session)
) -> User:
    """Require a role that may change operational resources."""
    if not can_manage_resources(current_user):
        logger.warning(
            "Rejected operator-only request from user %s (role '%s')",
            current_user.id,
            current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator privileges required",
        )
    return current_user


async def require_campaign_read_access(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session),
) -> User:
    from models.campaign import Campaign

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.deleted_at == None,
    ).first()
    if not campaign or not can_access_campaign(current_user, campaign):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return current_user


async def require_campaign_write_access(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> User:
    from models.campaign import Campaign

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.deleted_at == None,
    ).first()
    if not campaign or not can_access_campaign(current_user, campaign):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return current_user


async def verify_internal_key_or_campaign_reader(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db),
    x_internal_api_key: Optional[str] = Header(None),
):
    """Allow an internal service or a user authorized for the campaign."""
    expected_key = derive_campaign_api_key(INTERNAL_API_KEY, campaign_id)
    if x_internal_api_key and hmac.compare_digest(x_internal_api_key, expected_key):
        return None

    try:
        principal = await get_current_user_from_session(request, db)
    except HTTPException:
        raise HTTPException(403, "Invalid or missing credentials")

    from models.campaign import Campaign

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.deleted_at == None,
    ).first()
    if not campaign or not can_access_campaign(principal, campaign):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return principal
