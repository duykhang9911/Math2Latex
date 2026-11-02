from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models import Document, FormulaEntry


def _add_document(db, user, filename="bai1.pdf", status="ocr_complete", age_minutes=0, **extra):
    document = Document(
        id=uuid4(),
        filename=filename,
        status=status,
        uploaded_by=user.id if user else None,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=age_minutes),
        **extra,
    )
    db.add(document)
    db.commit()
    return document


def _add_formula(db, document, status="ocr_complete", page_number=1, latex_raw="x", latex_final=None):
    formula = FormulaEntry(
        id=uuid4(),
        document_id=document.id,
        page_number=page_number,
        status=status,
        latex_raw=latex_raw,
        latex_final=latex_final,
    )
    db.add(formula)
    db.commit()
    return formula


def test_upload_records_size_and_returns_document_id(make_client, make_user, db_session, upload_dir, enqueued_jobs):
    user = make_user("alice")
    client = make_client(user)

    response = client.post("/api/documents/upload", files={"file": ("de thi.pdf", b"%PDF-1.4 fake", "application/pdf")})

    assert response.status_code == 200, response.text
    body = response.json()
    document = db_session.get(Document, __import__("uuid").UUID(body["document_id"]))
    assert document.file_size_bytes == len(b"%PDF-1.4 fake")
    assert document.uploaded_by == user.id
    assert len(enqueued_jobs) == 1


def test_list_returns_only_own_documents_newest_first_with_counts(make_client, make_user, db_session):
    alice, bob = make_user("alice"), make_user("bob")
    old = _add_document(db_session, alice, "old.pdf", age_minutes=60, file_size_bytes=100, page_count=2)
    new = _add_document(db_session, alice, "new.pdf", age_minutes=1)
    _add_document(db_session, bob, "bob.pdf")
    _add_document(db_session, None, "orphan.pdf")
    _add_formula(db_session, old, status="submitted", latex_final="a")
    _add_formula(db_session, old, status="ocr_complete")

    response = make_client(alice).get("/api/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["filename"] for item in body["items"]] == ["new.pdf", "old.pdf"]
    assert body["items"][0]["document_id"] == str(new.id)
    old_item = body["items"][1]
    assert (old_item["formula_count"], old_item["submitted_count"]) == (2, 1)
    assert (old_item["file_size_bytes"], old_item["page_count"]) == (100, 2)
    assert body["items"][0]["formula_count"] == 0


def test_list_pagination_and_status_filter(make_client, make_user, db_session):
    alice = make_user("alice")
    for index in range(5):
        _add_document(db_session, alice, f"d{index}.pdf", age_minutes=index)
    _add_document(db_session, alice, "failed.pdf", status="processing_failed", age_minutes=10)
    client = make_client(alice)

    page = client.get("/api/documents", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 6
    assert [item["filename"] for item in page["items"]] == ["d2.pdf", "d3.pdf"]

    failed = client.get("/api/documents", params={"status": "processing_failed"}).json()
    assert failed["total"] == 1
    assert failed["items"][0]["filename"] == "failed.pdf"


def test_list_rejects_out_of_range_paging(make_client, make_user):
    client = make_client(make_user("alice"))

    assert client.get("/api/documents", params={"limit": 0}).status_code == 422
    assert client.get("/api/documents", params={"limit": 101}).status_code == 422
    assert client.get("/api/documents", params={"offset": -1}).status_code == 422


def test_history_requires_login(make_client, make_user):
    from fastapi.testclient import TestClient

    from app.main import app

    make_client(make_user("alice"))  # cài dependency override
    client = TestClient(app)

    assert client.get("/api/documents").status_code == 401


def test_get_document_detail_and_log(make_client, make_user, db_session, logged_actions):
    alice = make_user("alice")
    document = _add_document(db_session, alice, "bai.pdf")
    _add_formula(db_session, document, status="submitted", latex_final="y")

    response = make_client(alice).get(f"/api/documents/{document.id}")

    assert response.status_code == 200
    assert response.json()["submitted_count"] == 1
    assert {"action": "history_open", "ref_id": document.id, "detail": None, "user_id": alice.id} in logged_actions


def test_other_users_document_is_404_everywhere(make_client, make_user, db_session, upload_dir):
    alice, bob = make_user("alice"), make_user("bob")
    document = _add_document(db_session, alice)
    (upload_dir / str(document.id)).mkdir()
    (upload_dir / str(document.id) / "source.pdf").write_bytes(b"%PDF")
    client = make_client(bob)

    assert client.get(f"/api/documents/{document.id}").status_code == 404
    assert client.get(f"/api/documents/{document.id}/source").status_code == 404
    assert client.get(f"/api/documents/{document.id}/export").status_code == 404
    assert client.delete(f"/api/documents/{document.id}").status_code == 404
    assert db_session.get(Document, document.id) is not None


def test_orphan_document_is_not_visible(make_client, make_user, db_session):
    alice = make_user("alice")
    orphan = _add_document(db_session, None, "orphan.pdf")

    assert make_client(alice).get(f"/api/documents/{orphan.id}").status_code == 404


def test_delete_removes_rows_and_files(make_client, make_user, db_session, upload_dir, logged_actions):
    alice = make_user("alice")
    document = _add_document(db_session, alice)
    formula = _add_formula(db_session, document)
    document_id, formula_id = document.id, formula.id
    directory = upload_dir / str(document_id)
    (directory / "pages").mkdir(parents=True)
    (directory / "source.pdf").write_bytes(b"%PDF")

    response = make_client(alice).delete(f"/api/documents/{document_id}")

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(Document, document_id) is None
    assert db_session.get(FormulaEntry, formula_id) is None
    assert not directory.exists()
    assert any(entry["action"] == "history_delete" for entry in logged_actions)


def test_delete_succeeds_when_files_already_missing(make_client, make_user, db_session):
    alice = make_user("alice")
    document = _add_document(db_session, alice)

    assert make_client(alice).delete(f"/api/documents/{document.id}").status_code == 204


def test_delete_is_blocked_while_processing(make_client, make_user, db_session):
    alice = make_user("alice")
    client = make_client(alice)

    for status in ("processing_pages", "detecting_formulas", "ocr_processing"):
        document = _add_document(db_session, alice, status=status)
        assert client.delete(f"/api/documents/{document.id}").status_code == 409
        assert db_session.get(Document, document.id) is not None


def test_download_source_pdf(make_client, make_user, db_session, upload_dir):
    alice = make_user("alice")
    document = _add_document(db_session, alice, "đề thi.pdf")
    (upload_dir / str(document.id)).mkdir()
    (upload_dir / str(document.id) / "source.pdf").write_bytes(b"%PDF-1.4 content")
    client = make_client(alice)

    response = client.get(f"/api/documents/{document.id}/source")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 content"
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]


def test_download_source_pdf_missing_file_is_404(make_client, make_user, db_session):
    alice = make_user("alice")
    document = _add_document(db_session, alice)

    assert make_client(alice).get(f"/api/documents/{document.id}/source").status_code == 404


def test_export_contains_only_submitted_latex_final(make_client, make_user, db_session):
    alice = make_user("alice")
    document = _add_document(db_session, alice, "bai tập.pdf")
    _add_formula(db_session, document, status="submitted", page_number=2, latex_raw="RAW2", latex_final="b^2")
    _add_formula(db_session, document, status="submitted", page_number=1, latex_raw="RAW1", latex_final="a+b")
    _add_formula(db_session, document, status="ocr_complete", page_number=1, latex_raw="NOT_SUBMITTED")

    response = make_client(alice).get(f"/api/documents/{document.id}/export")

    assert response.status_code == 200
    text = response.text
    assert "a+b" in text and "b^2" in text
    assert text.index("a+b") < text.index("b^2")
    assert "RAW" not in text and "NOT_SUBMITTED" not in text
    assert "attachment" in response.headers["content-disposition"]
    assert ".tex" in response.headers["content-disposition"]


def test_export_without_submitted_formula_is_409(make_client, make_user, db_session):
    alice = make_user("alice")
    document = _add_document(db_session, alice)
    _add_formula(db_session, document, status="ocr_complete")

    assert make_client(alice).get(f"/api/documents/{document.id}/export").status_code == 409
