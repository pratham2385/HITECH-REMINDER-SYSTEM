"""Password hashing and signed-cookie helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import bcrypt

SESSION_MAX_AGE_SECONDS = 60 * 60 * 12


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    salt = bcrypt.gensalt()
    # bcrypt returns bytes, we decode to string for the database
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored bcrypt hash. Supports fallback if needed."""
    try:
        # Check if it's the old PBKDF2 hash
        if stored_hash.startswith("pbkdf2_sha256$"):
            algorithm, rounds, encoded_salt, encoded_digest = stored_hash.split("$", 3)
            salt = base64.b64decode(encoded_salt)
            expected_digest = base64.b64decode(encoded_digest)
            actual_digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                int(rounds),
            )
            return hmac.compare_digest(actual_digest, expected_digest)
        
        # Native bcrypt verify
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False


def sign_session(user_id: int, secret_key: str) -> str:
    """Create a signed session cookie value."""

    expires_at = int(time.time()) + SESSION_MAX_AGE_SECONDS
    payload = f"{user_id}:{expires_at}"
    signature = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode("utf-8")).decode("ascii")


def verify_session(cookie_value: str, secret_key: str) -> int | None:
    """Return the user id from a valid session cookie."""

    try:
        decoded = base64.urlsafe_b64decode(cookie_value.encode("ascii")).decode("utf-8")
        user_id_text, expires_at_text, signature = decoded.split(":", 2)
        payload = f"{user_id_text}:{expires_at_text}"
        expected = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        if int(expires_at_text) < int(time.time()):
            return None
        return int(user_id_text)
    except Exception:
        return None

