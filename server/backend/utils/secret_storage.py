"""Authenticated encryption for secrets persisted in SQLite."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


ENCRYPTED_PREFIX = "enc:v1:"


def _cipher() -> Fernet:
    source_key = os.environ["DATA_ENCRYPTION_KEY"]
    if len(source_key) < 32:
        raise RuntimeError("DATA_ENCRYPTION_KEY is too short")
    derived_key = base64.urlsafe_b64encode(
        hashlib.sha256(source_key.encode("utf-8")).digest()
    )
    return Fernet(derived_key)


def encrypt_secret(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if value.startswith(ENCRYPTED_PREFIX):
        decrypt_secret(value)
        return value
    encrypted = _cipher().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{encrypted}"


def decrypt_secret(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if not value.startswith(ENCRYPTED_PREFIX):
        return value
    try:
        plaintext = _cipher().decrypt(
            value[len(ENCRYPTED_PREFIX):].encode("ascii")
        )
    except (InvalidToken, ValueError) as exc:
        raise RuntimeError("Stored secret cannot be decrypted") from exc
    return plaintext.decode("utf-8")


def migrate_legacy_smtp_secrets() -> int:
    from database import SessionLocal
    from models.sending_profile import SMTPProfile

    db = SessionLocal()
    migrated = 0
    try:
        for profile in db.query(SMTPProfile).all():
            for field_name in ("smtp_password", "dkim_private_key"):
                value = getattr(profile, field_name)
                encrypted = encrypt_secret(value)
                if encrypted != value:
                    setattr(profile, field_name, encrypted)
                    migrated += 1
        if migrated:
            db.commit()
        return migrated
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
