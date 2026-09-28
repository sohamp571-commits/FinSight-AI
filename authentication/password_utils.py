

import hashlib
from datetime import datetime, timedelta

from config import config
from custom_exceptions import ValidationError
from helper import generate_secure_token, hash_password, verify_password
from logging_config import logger

RESET_TOKEN_VALIDITY_MINUTES: int = 30


def create_password_hash(plain_password: str) -> str:
    """Hash a plaintext password using the project's configured bcrypt rounds."""
    return hash_password(plain_password, rounds=config.BCRYPT_ROUNDS)


def check_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return verify_password(plain_password, password_hash)


def generate_reset_token() -> tuple[str, str, datetime]:
    """
    Generate a new password-reset token.

    Returns:
        A tuple of (raw_token, token_hash, expires_at):
            raw_token   - sent to the user (e.g. in the reset link), never persisted.
            token_hash  - SHA-256 hex digest, safe to store in password_reset_tokens.
            expires_at  - UTC datetime after which the token is no longer valid.
    """
    raw_token = generate_secure_token(length=32)
    token_hash = hash_reset_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_VALIDITY_MINUTES)
    logger.info("Password reset token generated.")
    return raw_token, token_hash, expires_at


def hash_reset_token(raw_token: str) -> str:
    """Deterministically hash a raw reset token for storage/lookup (SHA-256)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def is_token_expired(expires_at: datetime) -> bool:
    """Return True if the given token expiry timestamp is in the past."""
    return datetime.utcnow() > expires_at


def validate_new_password_pair(new_password: str, confirm_password: str) -> None:
    """Ensure a new password (from reset/change-password flows) is confirmed correctly."""
    if new_password != confirm_password:
        raise ValidationError("New password and confirmation do not match.")
    if len(new_password) < 8:
        raise ValidationError("New password must be at least 8 characters long.")
