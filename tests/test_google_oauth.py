"""Google OAuth flow tests (Google token/userinfo endpoints are mocked)."""

import pytest

from app.core.config import settings
from app.models.user import User
from app.services import google_oauth


@pytest.fixture
def google_config(monkeypatch):
    """Enable Google OAuth settings for the duration of a test."""
    monkeypatch.setattr(
        settings, "google_client_id", "test-client.apps.googleusercontent.com"
    )
    monkeypatch.setattr(settings, "google_client_secret", "test-secret")
    monkeypatch.setattr(
        settings,
        "google_redirect_uri",
        "http://localhost:8000/api/v1/auth/google/callback",
    )
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:5173")


def test_google_login_returns_auth_url(client, google_config):
    resp = client.get("/api/v1/auth/google/login")
    assert resp.status_code == 200
    url = resp.json()["auth_url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=test-client.apps.googleusercontent.com" in url
    assert "response_type=code" in url
    assert "state=" in url


def test_google_login_unconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")
    monkeypatch.setattr(settings, "google_redirect_uri", "")
    resp = client.get("/api/v1/auth/google/login")
    assert resp.status_code == 400
    assert "not configured" in resp.json()["detail"]


def test_google_callback_provisions_user(client, google_config, monkeypatch, db):
    state = google_oauth._sign_state()

    def fake_token(code):
        assert code == "google-code-1"
        return {"access_token": "google-at-1", "token_type": "Bearer"}

    def fake_userinfo(access_token):
        assert access_token == "google-at-1"
        return {"id": "123", "email": "alice.oauth@gmail.com", "name": "Alice OAuth"}

    monkeypatch.setattr(google_oauth, "_post_token", fake_token)
    monkeypatch.setattr(google_oauth, "_get_userinfo", fake_userinfo)

    resp = client.get(
        f"/api/v1/auth/google/callback?code=google-code-1&state={state}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("http://localhost:5173/oauth/callback#access_token=")

    user = db.query(User).filter(User.email == "alice.oauth@gmail.com").first()
    assert user is not None
    assert user.full_name == "Alice OAuth"
    # The first account ever created (no demo users anymore) bootstraps as admin.
    assert user.role.value == "administrator"


def test_google_callback_reuses_existing_user(client, google_config, monkeypatch, db):
    # Pre-register the same email with password auth.
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Existing",
            "email": "bob.oauth@gmail.com",
            "password": "secret123",
            "role": "security_manager",
        },
    )

    state = google_oauth._sign_state()

    def fake_token(code):
        return {"access_token": "google-at-2"}

    def fake_userinfo(access_token):
        return {"id": "456", "email": "bob.oauth@gmail.com", "name": "Bob Google"}

    monkeypatch.setattr(google_oauth, "_post_token", fake_token)
    monkeypatch.setattr(google_oauth, "_get_userinfo", fake_userinfo)

    resp = client.get(
        f"/api/v1/auth/google/callback?code=google-code-2&state={state}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "#access_token=" in resp.headers["location"]

    # Same user row, role preserved, no duplicate created.
    user = db.query(User).filter(User.email == "bob.oauth@gmail.com").first()
    assert user is not None
    assert user.role.value == "security_manager"
    count = db.query(User).filter(User.email == "bob.oauth@gmail.com").count()
    assert count == 1


def test_google_callback_second_user_is_analyst(client, google_config, monkeypatch, db):
    """A Google user created after the first one defaults to security_analyst."""
    # First user (bootstrap) -> administrator
    state = google_oauth._sign_state()
    monkeypatch.setattr(
        google_oauth, "_post_token", lambda code: {"access_token": "at-1"}
    )
    monkeypatch.setattr(
        google_oauth,
        "_get_userinfo",
        lambda at: {"id": "1", "email": "first@gmail.com", "name": "First"},
    )
    client.get(
        f"/api/v1/auth/google/callback?code=c1&state={state}",
        follow_redirects=False,
    )
    assert (
        db.query(User).filter(User.email == "first@gmail.com").first().role.value
        == "administrator"
    )

    # Second user -> analyst
    state2 = google_oauth._sign_state()
    monkeypatch.setattr(
        google_oauth,
        "_get_userinfo",
        lambda at: {"id": "2", "email": "second@gmail.com", "name": "Second"},
    )
    client.get(
        f"/api/v1/auth/google/callback?code=c2&state={state2}",
        follow_redirects=False,
    )
    assert (
        db.query(User).filter(User.email == "second@gmail.com").first().role.value
        == "security_analyst"
    )


def test_google_callback_rejects_forged_state(client, google_config):
    resp = client.get(
        "/api/v1/auth/google/callback?code=google-code-3&state=forged-state",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "#error=invalid_state" in resp.headers["location"]


def test_google_callback_handles_exchange_failure(client, google_config, monkeypatch):
    state = google_oauth._sign_state()

    def boom(code):
        raise RuntimeError("google is down")

    monkeypatch.setattr(google_oauth, "_post_token", boom)

    resp = client.get(
        f"/api/v1/auth/google/callback?code=google-code-4&state={state}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "#error=token_exchange_failed" in resp.headers["location"]
