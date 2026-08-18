"""
Google OAuth 2.0 (authorization code flow) for the SPA frontend.

Flow:
    1. Frontend calls ``GET /api/v1/auth/google/login`` and redirects the
       browser to the returned Google consent URL.
    2. Google redirects back to ``/api/v1/auth/google/callback`` with a
       ``code`` (plus a signed ``state`` we issued to prevent CSRF).
    3. The callback exchanges the code for an access token, fetches the
       user's profile, provisions a local user, and redirects the browser
       to ``FRONTEND_URL/oauth/callback#access_token=...``.

The token exchange uses ``httpx`` (already a project dependency).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import jwt, JWTError

from app.core.config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

_OAUTH_STATE_TTL_MINUTES = 10


def is_configured() -> bool:
    """True when Google OAuth credentials are present in the environment."""
    return bool(
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_redirect_uri
    )


def build_auth_url() -> str:
    """Build the Google consent URL with a signed CSRF-protection state."""
    state = _sign_state()
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
            "state": state,
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


def _sign_state() -> str:
    """Stateless signed state token so the callback can verify it came from us."""
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "exp": datetime.utcnow() + timedelta(minutes=_OAUTH_STATE_TTL_MINUTES),
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def verify_state(state: str | None) -> bool:
    """Validate the state token echoed back by Google (CSRF protection)."""
    if not state:
        return False
    try:
        jwt.decode(
            state, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return True
    except JWTError:
        return False


def _post_token(code: str) -> dict[str, Any]:
    """Exchange the authorization code for Google tokens."""
    resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _get_userinfo(access_token: str) -> dict[str, Any]:
    """Fetch the Google profile for an access token."""
    resp = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def exchange_code(code: str) -> dict[str, Any]:
    """Exchange an authorization code for the user's Google profile."""
    tokens = _post_token(code)
    return _get_userinfo(tokens["access_token"])
