"""
Dashboard authentication for Cheat Clip PRO.

Enabled only when BOTH ``DASHBOARD_LOGIN_USERNAME`` and
``DASHBOARD_LOGIN_PASSWORD`` environment variables are set. When they are not
set, the dashboard stays open (backwards compatible / local desktop use).

Sessions are stateless: an HMAC-signed token is stored in an HTTP-only cookie,
so no server-side session store is required and the token survives restarts.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

SESSION_COOKIE = "ccp_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _username() -> str:
    return (os.environ.get("DASHBOARD_LOGIN_USERNAME") or "").strip()


def _password() -> str:
    return (os.environ.get("DASHBOARD_LOGIN_PASSWORD") or "").strip()


def auth_enabled() -> bool:
    """Authentication is required only when both credentials are configured."""
    return bool(_username() and _password())


def _secret() -> bytes:
    secret = (os.environ.get("DASHBOARD_SESSION_SECRET") or "").strip()
    if not secret:
        # Derive a stable secret from the credentials so tokens remain valid
        # across container restarts even without an explicit session secret.
        secret = f"{_username()}::{_password()}::cheat-clip-pro"
    return secret.encode("utf-8")


def verify_credentials(username: str, password: str) -> bool:
    if not auth_enabled():
        return False
    return hmac.compare_digest((username or ""), _username()) and hmac.compare_digest(
        (password or ""), _password()
    )


def _sign(payload_b64: str) -> str:
    return hmac.new(_secret(), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_token(username: str, ttl: int = SESSION_TTL_SECONDS) -> str:
    payload = json.dumps({"u": username, "exp": int(time.time()) + int(ttl)})
    b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{b64}.{_sign(b64)}"


def verify_session_token(token: Optional[str]) -> Optional[str]:
    """Returns the authenticated username, or None if the token is missing/invalid/expired."""
    if not token or "." not in token:
        return None
    b64, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(b64)):
        return None
    try:
        padded = b64 + "=" * (-len(b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload.get("u")
