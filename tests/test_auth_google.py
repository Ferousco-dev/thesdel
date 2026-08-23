"""Tests for Google Sign-In (docs/DECISIONS.md ADR-011). Mocks
verify_google_id_token rather than hitting Google's real servers — the
verification logic itself (signature/issuer/audience) is google-auth's
responsibility, not ours; we're testing our own find-or-create/linking
logic on top of it.
"""

from unittest.mock import patch

import pytest

from app.shared.errors import InvalidCredentialsError


def _mock_claims(**overrides):
    claims = {
        "sub": "google-user-123",
        "email": "student@example.com",
        "email_verified": True,
        "name": "Ada Student",
        "iss": "accounts.google.com",
    }
    claims.update(overrides)
    return claims


async def test_new_google_user_is_created_and_logged_in(client):
    with patch("app.auth.service.verify_google_id_token", return_value=_mock_claims()):
        resp = await client.post("/v1/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "student@example.com"
    assert body["user"]["tier"] == "free"
    assert "access_token" in body and "refresh_token" in body


async def test_returning_google_user_logs_in_without_duplicate(client):
    claims = _mock_claims()
    with patch("app.auth.service.verify_google_id_token", return_value=claims):
        first = await client.post("/v1/auth/google", json={"id_token": "fake-token"})
        second = await client.post("/v1/auth/google", json={"id_token": "fake-token"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user"]["id"] == second.json()["user"]["id"]


async def test_google_links_to_existing_verified_password_account(client):
    register = await client.post(
        "/v1/auth/register",
        json={"email": "student@example.com", "password": "correct-horse-1", "display_name": "Ada"},
    )
    existing_user_id = register.json()["user"]["id"]

    with patch("app.auth.service.verify_google_id_token", return_value=_mock_claims()):
        resp = await client.post("/v1/auth/google", json={"id_token": "fake-token"})

    assert resp.status_code == 200
    assert resp.json()["user"]["id"] == existing_user_id


async def test_google_does_not_link_when_email_unverified(client):
    await client.post(
        "/v1/auth/register",
        json={"email": "student@example.com", "password": "correct-horse-1", "display_name": "Ada"},
    )

    with patch(
        "app.auth.service.verify_google_id_token",
        return_value=_mock_claims(email_verified=False),
    ):
        resp = await client.post("/v1/auth/google", json={"id_token": "fake-token"})

    assert resp.status_code == 401
    assert resp.json()["error_code"] == "invalid_credentials"


async def test_password_login_rejected_for_google_only_account(client):
    with patch("app.auth.service.verify_google_id_token", return_value=_mock_claims()):
        await client.post("/v1/auth/google", json={"id_token": "fake-token"})

    resp = await client.post(
        "/v1/auth/login", json={"email": "student@example.com", "password": "anything-at-all"}
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "invalid_credentials"


async def test_invalid_google_token_rejected(client):
    from app.shared.errors import UnauthenticatedError

    with patch(
        "app.auth.service.verify_google_id_token",
        side_effect=UnauthenticatedError("Could not verify Google sign-in."),
    ):
        resp = await client.post("/v1/auth/google", json={"id_token": "garbage"})
    assert resp.status_code == 401
