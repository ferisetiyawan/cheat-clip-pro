from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from backend.services.auth_service import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    auth_enabled,
    create_session_token,
    login_available,
    mcp_api_key_configured,
    verify_credentials,
    verify_mcp_api_key,
    verify_session_token,
)

router = APIRouter(tags=["Auth"])


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


def _extract_token(request: Request) -> Optional[str]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    return token


def is_authenticated(request: Request) -> bool:
    if not auth_enabled():
        return True
    return verify_session_token(_extract_token(request)) is not None


def _is_https(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    return forwarded == "https"


@router.get("/api/auth/status")
def auth_status(request: Request):
    required = auth_enabled()
    token = _extract_token(request)
    api_key = request.headers.get("x-api-key", "")
    username = verify_session_token(token) if required else None
    authenticated = (
        (not required)
        or bool(username)
        or verify_mcp_api_key(token or "")
        or verify_mcp_api_key(api_key)
    )
    return {
        "auth_required": required,
        "authenticated": authenticated,
        "username": username,
        "login_available": login_available(),
        "api_key_enabled": mcp_api_key_configured(),
    }


@router.post("/api/auth/login")
def auth_login(body: LoginRequest, request: Request, response: Response):
    if not auth_enabled():
        return {"success": True, "auth_required": False, "message": "Authentication is not enabled."}

    if not login_available():
        raise HTTPException(
            status_code=400,
            detail=(
                "Password login is not configured on this instance. It is protected by an "
                "API key (MCP_API_KEY) for programmatic access."
            ),
        )

    if not verify_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_session_token(body.username.strip())
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=_is_https(request),
        path="/",
    )
    return {"success": True, "auth_required": True, "username": body.username.strip()}


@router.post("/api/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"success": True}
