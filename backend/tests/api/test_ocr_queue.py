from uuid import uuid4

import pytest

from app.api import documents as documents_api
from app.models import Document, FormulaEntry


def _add_document(db, user, status="formula_proposals_ready"):
    document = Document(id=uuid4(), filename="bai1.pdf", status=status, uploaded_by=user.id)
    db.add(document)
    db.commit()
    return document


def _add_formulas(db, document, statuses):
    formulas = [
        FormulaEntry(id=uuid4(), document_id=document.id, page_number=1, status=status)
        for status in statuses
    ]
    db.add_all(formulas)
    db.commit()
    return formulas


def _statuses(db, document):
    db.expire_all()
    rows = db.query(FormulaEntry.status).filter(FormulaEntry.document_id == document.id).all()
    return sorted(status for (status,) in rows)


def _document_status(db, document):
    db.expire_all()
    return db.get(Document, document.id).status


def _redis_down(*_args):
    raise ConnectionError("redis unavailable")


def test_recognize_queues_one_job_and_marks_formulas_queued(make_client, make_user, db_session, enqueued_jobs):
    user = make_user("alice")
    document = _add_document(db_session, user)
    _add_formulas(db_session, document, ["proposed", "proposed"])

    response = make_client(user).post(f"/api/documents/{document.id}/formulas/recognize")

    assert response.status_code == 202, response.text
    assert response.json()["queued_count"] == 2
    assert len(enqueued_jobs) == 1
    assert _statuses(db_session, document) == ["ocr_queued", "ocr_queued"]
    assert _document_status(db_session, document) == "ocr_processing"


def test_second_recognize_is_rejected_and_does_not_enqueue_again(make_client, make_user, db_session, enqueued_jobs):
    user = make_user("alice")
    document = _add_document(db_session, user)
    _add_formulas(db_session, document, ["proposed"])
    client = make_client(user)

    first = client.post(f"/api/documents/{document.id}/formulas/recognize")
    second = client.post(f"/api/documents/{document.id}/formulas/recognize")

    assert first.status_code == 202
    assert second.status_code == 409
    assert len(enqueued_jobs) == 1


def test_recognize_requires_ready_document_and_existing_regions(make_client, make_user, db_session, enqueued_jobs):
    user = make_user("alice")
    client = make_client(user)
    processing = _add_document(db_session, user, status="detecting_formulas")
    empty = _add_document(db_session, user)

    assert client.post(f"/api/documents/{processing.id}/formulas/recognize").status_code == 409
    assert client.post(f"/api/documents/{empty.id}/formulas/recognize").status_code == 422
    assert enqueued_jobs == []


def test_recognize_of_another_users_document_is_404(make_client, make_user, db_session, enqueued_jobs):
    owner, other = make_user("alice"), make_user("bob")
    document = _add_document(db_session, owner)
    _add_formulas(db_session, document, ["proposed"])

    response = make_client(other).post(f"/api/documents/{document.id}/formulas/recognize")

    assert response.status_code == 404
    assert enqueued_jobs == []
    assert _statuses(db_session, document) == ["proposed"]


def test_recognize_restores_state_and_can_be_retried_when_redis_is_down(
    make_client, make_user, db_session, logged_actions, monkeypatch
):
    user = make_user("alice")
    document = _add_document(db_session, user)
    _add_formulas(db_session, document, ["proposed", "proposed"])
    client = make_client(user)
    monkeypatch.setattr(documents_api, "enqueue_job", _redis_down)

    failed = client.post(f"/api/documents/{document.id}/formulas/recognize")

    assert failed.status_code == 503
    assert _statuses(db_session, document) == ["proposed", "proposed"]
    assert _document_status(db_session, document) == "formula_proposals_ready"
    assert [entry["action"] for entry in logged_actions] == ["recognize_job_failed"]

    jobs = []
    monkeypatch.setattr(documents_api, "enqueue_job", lambda *args: jobs.append(args))
    retried = client.post(f"/api/documents/{document.id}/formulas/recognize")

    assert retried.status_code == 202
    assert len(jobs) == 1


def test_retry_requeues_only_failed_formulas_once(make_client, make_user, db_session, enqueued_jobs):
    user = make_user("alice")
    document = _add_document(db_session, user, status="ocr_completed_with_errors")
    _add_formulas(db_session, document, ["ocr_failed", "ocr_complete"])
    client = make_client(user)

    first = client.post(f"/api/documents/{document.id}/formulas/retry")
    second = client.post(f"/api/documents/{document.id}/formulas/retry")

    assert first.status_code == 202
    assert first.json()["queued_count"] == 1
    assert second.status_code == 409
    assert len(enqueued_jobs) == 1
    assert _statuses(db_session, document) == ["ocr_complete", "ocr_queued"]


def test_retry_without_failed_formulas_is_422(make_client, make_user, db_session, enqueued_jobs):
    user = make_user("alice")
    document = _add_document(db_session, user, status="ocr_completed_with_errors")
    _add_formulas(db_session, document, ["ocr_complete"])

    response = make_client(user).post(f"/api/documents/{document.id}/formulas/retry")

    assert response.status_code == 422
    assert enqueued_jobs == []


def test_retry_restores_failed_state_when_redis_is_down(
    make_client, make_user, db_session, logged_actions, monkeypatch
):
    user = make_user("alice")
    document = _add_document(db_session, user, status="ocr_completed_with_errors")
    _add_formulas(db_session, document, ["ocr_failed", "ocr_complete"])
    monkeypatch.setattr(documents_api, "enqueue_job", _redis_down)

    response = make_client(user).post(f"/api/documents/{document.id}/formulas/retry")

    assert response.status_code == 503
    assert _statuses(db_session, document) == ["ocr_complete", "ocr_failed"]
    assert _document_status(db_session, document) == "ocr_completed_with_errors"
    assert [entry["action"] for entry in logged_actions] == ["retry_job_failed"]


def test_upload_marks_document_failed_when_redis_is_down(make_client, make_user, db_session, monkeypatch):
    user = make_user("alice")
    monkeypatch.setattr(documents_api, "enqueue_job", _redis_down)

    response = make_client(user).post(
        "/api/documents/upload", files={"file": ("de thi.pdf", b"%PDF-1.4 fake", "application/pdf")}
    )

    assert response.status_code == 503
    db_session.expire_all()
    documents = db_session.query(Document).filter(Document.uploaded_by == user.id).all()
    assert [document.status for document in documents] == ["processing_failed"]


@pytest.mark.parametrize("status", ["processing_failed", "ocr_completed_with_errors"])
def test_retry_is_allowed_for_failed_document_states(make_client, make_user, db_session, enqueued_jobs, status):
    user = make_user("alice")
    document = _add_document(db_session, user, status=status)
    _add_formulas(db_session, document, ["ocr_failed"])

    response = make_client(user).post(f"/api/documents/{document.id}/formulas/retry")

    assert response.status_code == 202
    assert len(enqueued_jobs) == 1
