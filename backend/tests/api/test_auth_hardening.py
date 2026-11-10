from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
import pytest

from app.api import auth as auth_api
from app.core import rate_limit, security
from app.main import ALLOWED_ORIGINS
from app.models import User

PASSWORD = "correct-horse-123"


def _register(client, username="alice", password=PASSWORD):
    response = client.post("/api/auth/register", json={"username": username, "password": password})
    assert response.status_code == 201, response.text
    client.post("/api/auth/logout")
    client.cookies.clear()
    return response.json()


def _login(client, username="alice", password=PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password})


# --- giới hạn đăng nhập sai -------------------------------------------------------------------------------


def test_login_is_blocked_with_retry_after_after_repeated_failures(auth_client):
    client, _ = auth_client
    _register(client)

    assert [_login(client, password="wrong-password-1").status_code for _ in range(3)] == [401, 401, 401]
    blocked = _login(client)

    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60
    assert "math2latex_access" not in blocked.headers.get("set-cookie", "")


def test_successful_login_resets_the_failure_counter(auth_client):
    client, _ = auth_client
    _register(client)

    for _ in range(2):
        assert _login(client, password="wrong-password-1").status_code == 401
    assert _login(client).status_code == 200
    for _ in range(2):
        assert _login(client, password="wrong-password-1").status_code == 401

    assert _login(client).status_code == 200


def test_one_blocked_username_does_not_block_other_users_on_the_same_ip(auth_client):
    client, _ = auth_client
    _register(client, "alice")
    _register(client, "bob")
    for _ in range(3):
        _login(client, "alice", "wrong-password-1")

    assert _login(client, "alice").status_code == 429
    assert _login(client, "bob").status_code == 200


def test_unknown_usernames_are_counted_like_existing_ones(auth_client):
    client, _ = auth_client

    statuses = [_login(client, "ghost", "wrong-password-1").status_code for _ in range(4)]

    assert statuses == [401, 401, 401, 429]


def test_ip_wide_limit_stops_username_spraying(auth_client):
    client, _ = auth_client
    _register(client, "victim")
    for index in range(10):
        assert _login(client, f"guess{index}", "wrong-password-1").status_code == 401

    assert _login(client, "victim").status_code == 429


def test_login_still_works_when_the_rate_limit_store_is_down(auth_client, monkeypatch):
    client, _ = auth_client
    _register(client)

    class BrokenStore:
        def increment(self, *args):
            raise ConnectionError("redis down")

        get = delete = increment

    monkeypatch.setattr(rate_limit, "_limiter", rate_limit.LoginRateLimiter(BrokenStore()))

    assert _login(client, password="wrong-password-1").status_code == 401
    assert _login(client).status_code == 200


# --- cookie ---------------------------------------------------------------------------------------------------


def test_session_cookie_flags(auth_client):
    client, _ = auth_client
    _register(client)

    cookie = _login(client).headers["set-cookie"].lower()

    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/api" in cookie
    assert "secure" not in cookie.replace("samesite", "")


def test_session_cookie_is_secure_when_configured_for_https(auth_client, monkeypatch):
    client, _ = auth_client
    _register(client)
    monkeypatch.setattr(auth_api, "AUTH_COOKIE_SECURE", True)

    login = _login(client).headers["set-cookie"].lower()
    logout = client.post("/api/auth/logout").headers["set-cookie"].lower()

    assert "secure" in login and "httponly" in login
    assert "secure" in logout and "max-age=0" in logout


# --- token ----------------------------------------------------------------------------------------------------


def _forge(secret, **claims):
    payload = {"sub": str(uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=5), **claims}
    payload = {key: value for key, value in payload.items() if value is not None}
    return jwt.encode(payload, secret, algorithm="HS256" if secret else "none")


def _me_with_token(client, token):
    client.cookies.clear()
    client.cookies.set(security.ACCESS_COOKIE_NAME, token, path="/api")
    return client.get("/api/auth/me")


@pytest.mark.parametrize(
    "make_token",
    [
        lambda user_id: _forge(security.AUTH_SECRET, sub=user_id, exp=datetime.now(timezone.utc) - timedelta(seconds=1)),
        lambda user_id: _forge("another-secret-that-is-long-enough-123456", sub=user_id),
        lambda user_id: _forge(None, sub=user_id),
        lambda user_id: _forge(security.AUTH_SECRET, sub=user_id, exp=None),
        lambda user_id: _forge(security.AUTH_SECRET, sub="not-a-uuid"),
        lambda user_id: "garbage.token.value",
    ],
    ids=["expired", "wrong-signature", "alg-none", "missing-exp", "sub-not-uuid", "garbage"],
)
def test_invalid_tokens_are_rejected(auth_client, make_token):
    client, _ = auth_client
    user = _register(client)

    assert _me_with_token(client, make_token(user["id"])).status_code == 401


def test_token_of_a_deleted_user_is_rejected(auth_client):
    client, test_sessions = auth_client
    user = _register(client)
    token = security.create_access_token(UUID(user["id"]))
    with test_sessions() as db:
        db.query(User).delete()
        db.commit()

    assert _me_with_token(client, token).status_code == 401


def test_changing_auth_secret_invalidates_existing_sessions(auth_client, monkeypatch):
    client, _ = auth_client
    _register(client)
    assert _login(client).status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    monkeypatch.setattr(security, "AUTH_SECRET", "rotated-secret-that-is-long-enough-1234567")

    assert client.get("/api/auth/me").status_code == 401
    assert _login(client).status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_a_too_short_secret_never_authenticates(auth_client, monkeypatch):
    client, _ = auth_client
    user = _register(client)
    token = _forge(security.AUTH_SECRET, sub=user["id"])
    monkeypatch.setattr(security, "AUTH_SECRET", "short")

    assert _me_with_token(client, token).status_code == 401
    with pytest.raises(RuntimeError):
        security.create_access_token(uuid4())


# --- CSRF: kiểm tra Origin ------------------------------------------------------------------------------------


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "http://localhost:5174"])
@pytest.mark.parametrize("method", ["post", "patch", "delete"])
def test_writes_from_unknown_origins_are_rejected(auth_client, origin, method):
    client, _ = auth_client

    response = getattr(client, method)("/api/documents/00000000-0000-0000-0000-000000000000", headers={"Origin": origin})

    assert response.status_code == 403
    assert response.json() == {"detail": "Origin không được phép"}


def test_login_from_unknown_origin_is_rejected_before_touching_credentials(auth_client):
    client, _ = auth_client
    _register(client)

    response = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert "set-cookie" not in response.headers


def test_writes_from_allowed_origin_or_without_origin_are_not_blocked(auth_client):
    client, _ = auth_client

    assert client.post("/api/auth/logout", headers={"Origin": ALLOWED_ORIGINS[0]}).status_code == 204
    assert client.post("/api/auth/logout").status_code == 204


def test_reads_from_unknown_origins_are_not_blocked_by_the_origin_check(auth_client):
    client, _ = auth_client

    response = client.get("/api/auth/me", headers={"Origin": "https://evil.example"})

    assert response.status_code == 401  # chưa đăng nhập, không phải 403 của Origin check


# --- không lộ bí mật trong log ------------------------------------------------------------------------------


def test_passwords_and_tokens_are_never_logged(auth_client, caplog):
    client, _ = auth_client
    secret_password = "S3cret-Password-XYZ-987"
    caplog.set_level("DEBUG")

    _register(client, "alice", secret_password)
    _login(client, "alice", "wrong-Password-XYZ-123")
    login = _login(client, "alice", secret_password)
    token = login.cookies.get(security.ACCESS_COOKIE_NAME) or ""

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert secret_password not in logged
    assert "wrong-Password-XYZ-123" not in logged
    assert not token or token not in logged
