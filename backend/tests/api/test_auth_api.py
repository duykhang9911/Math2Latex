from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core import security
from app.main import app
from app.models import Document, User


@pytest.fixture
def auth_client(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, sessionmaker]]:
    database_path = tmp_path / "auth-test.sqlite"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    User.__table__.create(engine)
    Document.__table__.create(engine)
    test_sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(security, "AUTH_SECRET", "test-auth-secret-that-is-long-enough-123456")

    def override_get_db():
        session = test_sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, test_sessions
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_register_login_logout_and_password_hash(auth_client):
    client, test_sessions = auth_client
    registration = client.post(
        "/api/auth/register",
        json={"username": "Toan.User", "password": "correct-horse-123"},
    )

    assert registration.status_code == 201
    response_user = registration.json()
    assert response_user["username"] == "toan.user"
    assert "password_hash" not in response_user
    assert "httponly" in registration.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").json()["id"] == response_user["id"]

    with test_sessions() as db:
        stored_user = db.get(User, UUID(response_user["id"]))
        assert stored_user.password_hash != "correct-horse-123"
        assert stored_user.password_hash.startswith("$argon2")

    duplicate = client.post(
        "/api/auth/register",
        json={"username": "TOAN.USER", "password": "another-password-123"},
    )
    assert duplicate.status_code == 409

    bad_login = client.post(
        "/api/auth/login",
        json={"username": "toan.user", "password": "wrong-password-123"},
    )
    assert bad_login.status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"username": "TOAN.USER", "password": "correct-horse-123"},
    )
    assert login.status_code == 200
    assert login.json()["id"] == response_user["id"]

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_document_is_visible_only_to_owner(auth_client):
    client, test_sessions = auth_client
    first = client.post(
        "/api/auth/register",
        json={"username": "owner.one", "password": "owner-password-123"},
    ).json()
    document_id = uuid4()
    with test_sessions() as db:
        db.add(
            Document(
                id=document_id,
                filename="private.pdf",
                status="uploaded",
                uploaded_by=UUID(first["id"]),
            )
        )
        db.commit()

    own_document = client.get(f"/api/documents/{document_id}/pages")
    assert own_document.status_code == 200

    second = client.post(
        "/api/auth/register",
        json={"username": "owner.two", "password": "second-password-123"},
    )
    assert second.status_code == 201
    other_document = client.get(f"/api/documents/{document_id}/pages")
    assert other_document.status_code == 404