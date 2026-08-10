# admin-backend/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List
import uuid
import logging
import re
import secrets
import string

from database import get_db
from models.user import User
from models.campaign import Campaign
from routes.auth import get_current_user_from_session, require_admin
from utils.auth import hash_password, verify_password
from utils.permissions import VALID_USER_ROLES
from utils.session_auth import clear_session_cookie, revoke_user_sessions

router = APIRouter()
logger = logging.getLogger(__name__)
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$")
MIN_PASSWORD_LENGTH = 12
GENERATED_PASSWORD_LENGTH = 20
PASSWORD_SPECIAL_CHARACTERS = "!@#$%&*+-_"


def generate_temporary_password() -> str:
    """Generate a strong credential that is only returned once to the caller."""
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(PASSWORD_SPECIAL_CHARACTERS),
    ]
    alphabet = string.ascii_letters + string.digits + PASSWORD_SPECIAL_CHARACTERS
    required.extend(
        secrets.choice(alphabet)
        for _ in range(GENERATED_PASSWORD_LENGTH - len(required))
    )
    secrets.SystemRandom().shuffle(required)
    return "".join(required)


# ========================================
# PYDANTIC MODELS
# ========================================

class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    role: str = Field(default="operator", max_length=16)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    email: Optional[EmailStr] = None
    role: Optional[str] = Field(default=None, max_length=16)
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    old_password: str = Field(min_length=1, max_length=1024)


class AdminPasswordReset(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    last_login: Optional[str]


class CreatedUserResponse(UserResponse):
    temporary_password: str


class GeneratedPasswordResponse(BaseModel):
    message: str
    temporary_password: str


# ========================================
# ENDPOINTS
# ========================================

@router.get("", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # ✅ Only admin
):
    """Get all users (admin only)"""
    users = db.query(User).all()
    return [u.to_dict() for u in users]


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_from_session)
):
    """Get current authenticated user"""
    return current_user.to_dict()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get user by ID (self or admin)"""

    # Users can view themselves, admins can view anyone
    if current_user.id != user_id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    return user.to_dict()


@router.post("", response_model=CreatedUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # ✅ Only admin
):
    """Create new user (admin only)"""
    response.headers["Cache-Control"] = "no-store"

    username = user_data.username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(
            400,
            "Username must be 3-64 characters and contain only letters, "
            "numbers, dots, dashes, or underscores",
        )

    if user_data.role not in VALID_USER_ROLES:
        valid_roles = ", ".join(sorted(VALID_USER_ROLES))
        raise HTTPException(400, f"Invalid role. Must be one of: {valid_roles}")

    # Check if username exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(400, f"Username '{username}' already exists")

    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(400, f"Email '{user_data.email}' already exists")

    temporary_password = generate_temporary_password()

    # Create user
    new_user = User(
        id=str(uuid.uuid4())[:8],
        username=username,
        email=user_data.email,
        password=hash_password(temporary_password),
        role=user_data.role,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"✅ User created: {new_user.username} (by {current_user.username})")

    return {**new_user.to_dict(), "temporary_password": temporary_password}


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # ✅ Only admin
):
    """Update user (admin only)"""

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    revoke_sessions = False

    # Update fields
    if user_data.email is not None:
        # Check if email already exists
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(400, f"Email '{user_data.email}' already exists")
        user.email = user_data.email

    if user_data.role is not None:
        if user_data.role not in VALID_USER_ROLES:
            valid_roles = ", ".join(sorted(VALID_USER_ROLES))
            raise HTTPException(400, f"Invalid role. Must be one of: {valid_roles}")
        if (
            user.role == "admin"
            and user_data.role != "admin"
            and _active_admin_count(db) <= 1
        ):
            raise HTTPException(400, "Cannot demote the last active admin user")
        user.role = user_data.role
        revoke_sessions = True

    if user_data.is_active is not None:
        # Prevent deactivating yourself
        if user.id == current_user.id and not user_data.is_active:
            raise HTTPException(400, "Cannot deactivate your own account")
        if (
            user.role == "admin"
            and not user_data.is_active
            and _active_admin_count(db) <= 1
        ):
            raise HTTPException(400, "Cannot deactivate the last active admin user")
        user.is_active = user_data.is_active
        revoke_sessions = True

    if revoke_sessions:
        revoke_user_sessions(db, user.id)

    db.commit()
    db.refresh(user)

    logger.info(f"✅ User updated: {user.username} (by {current_user.username})")

    return user.to_dict()


@router.post("/{user_id}/reset-password", response_model=GeneratedPasswordResponse)
async def reset_user_password(
    user_id: str,
    password_data: AdminPasswordReset,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Reset any user's password (admin only)."""
    response.headers["Cache-Control"] = "no-store"
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    temporary_password = generate_temporary_password()
    user.password = hash_password(temporary_password)
    revoke_user_sessions(db, user.id)
    db.commit()
    logger.info(
        "Password reset for user %s by %s",
        user.username,
        current_user.username,
    )
    return {
        "message": "Password reset successfully",
        "temporary_password": temporary_password,
    }


@router.post("/change-password", response_model=GeneratedPasswordResponse)
async def change_password(
    password_data: PasswordChange,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Change current user's password"""
    response.headers["Cache-Control"] = "no-store"

    # Verify old password
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password"
        )

    temporary_password = generate_temporary_password()
    current_user.password = hash_password(temporary_password)
    revoke_user_sessions(db, current_user.id)
    db.commit()
    clear_session_cookie(response)

    logger.info(f"✅ Password changed for user: {current_user.username}")

    return {
        "message": "Password changed successfully",
        "temporary_password": temporary_password,
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # ✅ Only admin
):
    """Delete user (admin only)"""

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot delete your own account")

    # Check if it's the last admin
    if user.role == "admin" and user.is_active:
        admin_count = _active_admin_count(db)
        if admin_count <= 1:
            raise HTTPException(400, "Cannot delete the last active admin user")

    reassigned_campaigns = db.query(Campaign).filter(
        Campaign.created_by == user.id
    ).update(
        {Campaign.created_by: current_user.id},
        synchronize_session=False,
    )
    db.delete(user)
    db.commit()

    logger.info(
        "User deleted: %s by %s; reassigned %s campaign(s)",
        user.username,
        current_user.username,
        reassigned_campaigns,
    )

    return {
        "status": "deleted",
        "id": user_id,
        "reassigned_campaigns": reassigned_campaigns,
    }


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(
        User.role == "admin",
        User.is_active.is_(True),
    ).count()
