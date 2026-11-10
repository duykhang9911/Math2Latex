"""Test đồng thời cho recognize trên PostgreSQL thật.

SQLite bỏ qua `SELECT ... FOR UPDATE` nên các test này chỉ chạy khi có database riêng:

    TEST_PG_URL=postgresql://user:pass@host:5432/ten_db_test python -m pytest tests/api/test_ocr_queue_concurrency.py

Dùng database tạm: fixture tạo bảng trước và xóa bảng sau mỗi test.
"""
import os
import threading
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import queue as job_queue
from app.core import security
from app.core.database import Base, get_db
from app.main import app
from app.models import Document, FormulaEntry, User
from app.services import action_log

TEST_PG_URL = os.getenv("TEST_PG_URL")

pytestmark = pytest.mark.skipif(not TEST_PG_URL, reason="Cần TEST_PG_URL trỏ tới database PostgreSQL tạm")


@pytest.fixture()
def pg_sessions(monkeypatch):
    engine = create_engine(TEST_PG_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def _get_db():
        db = sessions()
        try:
            yield db
        finally:
            db.close()

    jobs = []
    monkeypatch.setattr(security, "AUTH_SECRET", os.environ["AUTH_SECRET"])
    monkeypatch.setattr(job_queue, "enqueue_job", lambda *args, **kwargs: jobs.append(args))
    monkeypatch.setattr(action_log, "log_action", lambda *args, **kwargs: None)
    app.dependency_overrides[get_db] = _get_db
    yield sessions, jobs
    app.dependency_overrides.clear()
    engine.dispose()
    engine = create_engine(TEST_PG_URL)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _seed_ready_document(sessions):
    with sessions() as db:
        user = User(username=f"user-{uuid4().hex[:8]}", password_hash="x")
        db.add(user)
        db.flush()
        document = Document(id=uuid4(), filename="bai1.pdf", status="formula_proposals_ready", uploaded_by=user.id)
        db.add(document)
        db.flush()
        db.add(FormulaEntry(id=uuid4(), document_id=document.id, page_number=1, status="proposed"))
        db.commit()
        return user.id, document.id


def _client(user_id):
    client = TestClient(app)
    client.cookies.set(security.ACCESS_COOKIE_NAME, security.create_access_token(user_id), path="/api")
    return client


def test_two_simultaneous_recognize_requests_enqueue_exactly_one_job(pg_sessions):
    sessions, jobs = pg_sessions
    user_id, document_id = _seed_ready_document(sessions)
    barrier = threading.Barrier(2)
    codes = []

    def _post():
        client = _client(user_id)
        barrier.wait()
        codes.append(client.post(f"/api/documents/{document_id}/formulas/recognize").status_code)

    threads = [threading.Thread(target=_post) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(codes) == [202, 409]
    assert len(jobs) == 1


def test_recognize_waits_for_row_lock_then_sees_the_new_status(pg_sessions):
    sessions, jobs = pg_sessions
    user_id, document_id = _seed_ready_document(sessions)
    result = {}

    holder = sessions()
    holder.query(Document).filter(Document.id == document_id).with_for_update().first()

    def _post():
        result["status"] = _client(user_id).post(f"/api/documents/{document_id}/formulas/recognize").status_code

    thread = threading.Thread(target=_post)
    thread.start()
    thread.join(timeout=1.5)
    blocked = thread.is_alive()

    holder.query(Document).filter(Document.id == document_id).update({"status": "ocr_processing"})
    holder.commit()
    holder.close()
    thread.join(timeout=30)

    assert blocked, "Request phải chờ row lock thay vì đọc trạng thái cũ"
    assert result["status"] == 409
    assert jobs == []
