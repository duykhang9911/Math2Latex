from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from app.core import security
from app.schemas.auth import AuthCredentials


def test_password_hash_verifies_without_storing_plaintext():
    password = "sample-password-123"
    password_hash = security.hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2")
    assert security.verify_password(password, password_hash)
    assert not security.verify_password("wrong-password", password_hash)


def test_invalid_password_hash_is_rejected():
    assert not security.verify_password("password123", "not-an-argon2-hash")


def test_access_token_has_user_subject_and_expiration(monkeypatch: pytest.MonkeyPatch):
    secret = "unit-test-secret-that-is-long-enough-123456"
    monkeypatch.setattr(security, "AUTH_SECRET", secret)
    user_id = uuid4()

    token = security.create_access_token(user_id)
    claims = jwt.decode(token, secret, algorithms=["HS256"])

    assert claims["sub"] == str(user_id)
    now = datetime.now(timezone.utc)
    expires_at = datetime.fromtimestamp(claims["exp"], timezone.utc)
    assert expires_at > now
    assert expires_at <= now + timedelta(minutes=61)


@pytest.mark.parametrize(
    "username,password",
    [("ab", "password123"), ("valid_user", "short"), ("bad user", "password123")],
)
def test_auth_credentials_reject_invalid_values(username: str, password: str):
    with pytest.raises(ValidationError):
        AuthCredentials(username=username, password=password)


def test_auth_credentials_accept_valid_values():
    credentials = AuthCredentials(username="user.name_1", password="password123")

    assert credentials.username == "user.name_1"