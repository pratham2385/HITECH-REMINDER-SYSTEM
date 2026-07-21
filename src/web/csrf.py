"""Lightweight CSRF protection using signed tokens."""

import hmac
import hashlib
import time
import base64
import secrets
from fastapi import Request
from src.config.settings import load_settings

settings = load_settings()
CSRF_SECRET = settings.secret_key.encode('utf-8')

def generate_csrf_token(request: Request) -> str:
    """Generate a time-limited signed CSRF token."""
    # A simple token that expires in 1 hour
    expires_at = int(time.time()) + 3600
    # Include the user's IP or something specific to bind it loosely
    client_ip = request.client.host if request.client else "unknown"
    random_nonce = secrets.token_hex(8)
    
    payload = f"{expires_at}:{client_ip}:{random_nonce}"
    signature = hmac.new(CSRF_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    
    token = f"{payload}:{signature}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii")

def verify_csrf_token(request: Request, token: str) -> bool:
    """Verify the signed CSRF token."""
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        expires_at_text, client_ip, random_nonce, signature = decoded.split(":", 3)
        
        # Verify signature
        payload = f"{expires_at_text}:{client_ip}:{random_nonce}"
        expected = hmac.new(CSRF_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
            
        # Verify expiry
        if int(expires_at_text) < int(time.time()):
            return False
            
        # Verify IP binding
        current_ip = request.client.host if request.client else "unknown"
        if client_ip != current_ip:
            return False
            
        return True
    except Exception:
        return False
