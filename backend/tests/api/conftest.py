import os
import tempfile
from collections.abc import Iterator

# Phải đặt trước khi import app: database.py/security.py/documents.py đọc env lúc import.
os.environ.setdefault("DB_URL", "sqlite://")
os.environ.setdefault("AUTH_SECRET", "api-test-secret-that-is-long-enough-1234567890")
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="math2latex-test-uploads-"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import documents as documents_api
from app.core import security
from app.core.database import Base, get_db
from app.main import app
from app.models import Document, FormulaEntry, User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Bảng logs dùng JSONB (chỉ PostgreSQL) nên không tạo ở SQLite; _log_action được thay bằng bản ghi nhớ.
    Base.metadata.create_all(engine, tables=[User.__table__, Document.__table__, FormulaEntry.__table__])
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(documents_api, "UPLOAD_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def logged_actions(monkeypatch):
    entries = []

    def _log(db, action, ref_id=None, detail=None, user_id=None):
        entries.append({"action": action, "ref_id": ref_id, "detail": detail, "user_id": user_id})

    monkeypatch.setattr(documents_api, "_log_action", _log)
    return entries


@pytest.fixture()
def enqueued_jobs(monkeypatch):
    jobs = []
    monkeypatch.setattr(documents_api, "enqueue_job", lambda *args, **kwargs: jobs.append(args))
    return jobs


@pytest.fixture()
def make_client(db_session, upload_dir, logged_actions, enqueued_jobs, monkeypatch):
    monkeypatch.setattr(security, "AUTH_SECRET", os.environ["AUTH_SECRET"])
    app.dependency_overrides[get_db] = lambda: db_session

    def _make(user: User) -> TestClient:
        client = TestClient(app)
        client.cookies.set(security.ACCESS_COOKIE_NAME, security.create_access_token(user.id), path="/api")
        return client

    yield _make
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    def _make(username: str) -> User:
        user = User(username=username, password_hash="x")
        db_session.add(user)
        db_session.commit()
        return user

    return _make

@pytest.fixture()
def make_pdf():
    """Tạo PDF hợp lệ nhỏ bằng PyMuPDF: make_pdf(pages=1, size=(595, 842), password=None) -> bytes."""
    import pymupdf

    def _make(pages: int = 1, size: tuple[int, int] = (595, 842), password: str | None = None) -> bytes:
        document = pymupdf.open()
        for _ in range(pages):
            document.new_page(width=size[0], height=size[1])
        if password:
            data = document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password + "-owner")
        else:
            data = document.tobytes()
        document.close()
        return data

    return _make


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
