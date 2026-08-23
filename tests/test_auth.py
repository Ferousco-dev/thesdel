async def _register(client, email="student@example.com", password="correct-horse-1"):
    return await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Ada"},
    )


async def test_register_then_me(client):
    resp = await _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["tier"] == "free"

    me = await client.get(
        "/v1/users/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "student@example.com"


async def test_register_duplicate_email_rejected(client):
    await _register(client)
    resp = await _register(client)
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "conflict"


async def test_me_without_token_is_unauthenticated(client):
    resp = await client.get("/v1/users/me")
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "unauthenticated"


async def test_login_wrong_password_is_generic(client):
    await _register(client)
    resp = await client.post(
        "/v1/auth/login",
        json={"email": "student@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "invalid_credentials"


async def test_refresh_rotates_token_and_old_token_is_rejected(client):
    reg = await _register(client)
    refresh_token = reg.json()["refresh_token"]

    first_refresh = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first_refresh.status_code == 200
    new_refresh_token = first_refresh.json()["refresh_token"]
    assert new_refresh_token != refresh_token

    # Reusing the original (now-rotated-away) token must fail — reuse
    # detection per docs/SECURITY.md threat table.
    reuse_attempt = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_attempt.status_code == 401
    assert reuse_attempt.json()["error_code"] == "token_invalid"

    # And the family is now fully revoked — even the newly-rotated token
    # must be rejected, since reuse is a theft signal.
    second_use_of_new_token = await client.post(
        "/v1/auth/refresh", json={"refresh_token": new_refresh_token}
    )
    assert second_use_of_new_token.status_code == 401


async def test_logout_revokes_refresh_token(client):
    reg = await _register(client)
    refresh_token = reg.json()["refresh_token"]

    logout_resp = await client.post("/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    refresh_after_logout = await client.post(
        "/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_after_logout.status_code == 401


async def test_login_rate_limited_after_max_attempts(client, monkeypatch):
    from app.shared.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("RATE_LIMIT_LOGIN_MAX", "2")
    get_settings.cache_clear()

    await _register(client)

    for _ in range(2):
        resp = await client.post(
            "/v1/auth/login",
            json={"email": "student@example.com", "password": "wrong-password"},
        )
        assert resp.status_code == 401

    limited = await client.post(
        "/v1/auth/login",
        json={"email": "student@example.com", "password": "wrong-password"},
    )
    assert limited.status_code == 429
    assert limited.json()["error_code"] == "rate_limited"

    get_settings.cache_clear()
