from uuid import uuid4

import pytest

from app.api import documents as documents_api
from app.core import limits
from app.models import Document, FormulaEntry
from app.services import formula_ocr, pdf_pages


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


def _redis_down(*_args, **_kwargs):
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
    monkeypatch.setattr(documents_api, "enqueue_job", lambda *args, **kwargs: jobs.append(args))
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


def test_upload_marks_document_failed_when_redis_is_down(make_client, make_user, db_session, monkeypatch, make_pdf):
    user = make_user("alice")
    monkeypatch.setattr(documents_api, "enqueue_job", _redis_down)

    response = make_client(user).post(
        "/api/documents/upload", files={"file": ("de thi.pdf", make_pdf(), "application/pdf")}
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

def test_jobs_are_enqueued_with_failure_callbacks_and_timeouts(make_client, make_user, db_session, monkeypatch, make_pdf):
    user = make_user("alice")
    client = make_client(user)
    calls = []
    monkeypatch.setattr(documents_api, "enqueue_job", lambda *args, **kwargs: calls.append((args, kwargs)))

    client.post("/api/documents/upload", files={"file": ("de thi.pdf", make_pdf(), "application/pdf")})
    recognizable = _add_document(db_session, user)
    _add_formulas(db_session, recognizable, ["proposed"])
    client.post(f"/api/documents/{recognizable.id}/formulas/recognize")
    retryable = _add_document(db_session, user, status="ocr_completed_with_errors")
    _add_formulas(db_session, retryable, ["ocr_failed"])
    client.post(f"/api/documents/{retryable.id}/formulas/retry")

    callbacks = [kwargs["on_failure"] for _args, kwargs in calls]
    assert callbacks == [
        pdf_pages.mark_pdf_job_failed,
        formula_ocr.mark_ocr_job_failed,
        formula_ocr.mark_ocr_job_failed,
    ]
    assert [kwargs["job_timeout"] for _args, kwargs in calls] == [
        limits.PDF_JOB_TIMEOUT_SECONDS,
        limits.OCR_JOB_TIMEOUT_SECONDS,
        limits.OCR_JOB_TIMEOUT_SECONDS,
    ]

@pytest.mark.parametrize(
    ("endpoint", "document_status", "before", "after"),
    [
        ("recognize", "formula_proposals_ready", "proposed", "ocr_queued"),
        ("retry", "ocr_completed_with_errors", "ocr_failed", "ocr_queued"),
    ],
)
def test_log_failure_after_enqueue_does_not_roll_back_queued_state(
    make_client, make_user, db_session, enqueued_jobs, monkeypatch, endpoint, document_status, before, after
):
    user = make_user("alice")
    document = _add_document(db_session, user, status=document_status)
    _add_formulas(db_session, document, [before])

    def _broken_log(*_args, **_kwargs):
        raise RuntimeError("logs table unavailable")

    monkeypatch.setattr(documents_api, "_log_action", _broken_log)

    response = make_client(user).post(f"/api/documents/{document.id}/formulas/{endpoint}")

    assert response.status_code == 202
    assert len(enqueued_jobs) == 1
    assert _statuses(db_session, document) == [after]
    assert _document_status(db_session, document) == "ocr_processing"
