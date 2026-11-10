from uuid import UUID

import pytest

from app.api import documents as documents_api
from app.models import Document
from app.services import upload_validation


def _upload(client, name, content, content_type="application/pdf"):
    return client.post("/api/documents/upload", files={"file": (name, content, content_type)})


def _only_document(db_session):
    db_session.expire_all()
    return db_session.query(Document).one()


def test_valid_pdf_is_accepted_and_page_count_is_recorded(make_client, make_user, db_session, upload_dir, enqueued_jobs, make_pdf):
    response = _upload(make_client(make_user("alice")), "bai1.pdf", make_pdf(pages=3))

    assert response.status_code == 200, response.text
    document = db_session.get(Document, UUID(response.json()["document_id"]))
    assert document.page_count == 3
    assert (upload_dir / str(document.id) / "source.pdf").is_file()
    assert len(enqueued_jobs) == 1


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("bai1.pdf", b"this is not a pdf"),
        ("bai1.pdf", b""),
        ("bai1.pdf", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64),
        ("bai1.pdf", b"%PDF-1.4 fake"),
    ],
)
def test_corrupt_or_non_pdf_content_is_rejected_and_leaves_nothing_behind(
    make_client, make_user, db_session, upload_dir, enqueued_jobs, name, content
):
    response = _upload(make_client(make_user("alice")), name, content)

    assert response.status_code == 400
    assert db_session.query(Document).count() == 0
    assert list(upload_dir.iterdir()) == []
    assert enqueued_jobs == []


def test_a_real_image_renamed_to_pdf_is_rejected(make_client, make_user, upload_dir, enqueued_jobs):
    import pymupdf

    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 8, 8), False)
    pixmap.clear_with(255)
    response = _upload(make_client(make_user("alice")), "scan.pdf", pixmap.tobytes("png"))

    assert response.status_code == 400
    assert list(upload_dir.iterdir()) == []


def test_password_protected_pdf_is_rejected(make_client, make_user, db_session, upload_dir, enqueued_jobs, make_pdf):
    response = _upload(make_client(make_user("alice")), "bai1.pdf", make_pdf(password="secret"))

    assert response.status_code == 400
    assert "mật khẩu" in response.json()["detail"]
    assert db_session.query(Document).count() == 0
    assert list(upload_dir.iterdir()) == []


def test_pdf_with_too_many_pages_is_rejected(make_client, make_user, db_session, upload_dir, enqueued_jobs, make_pdf, monkeypatch):
    monkeypatch.setattr(upload_validation, "MAX_PDF_PAGES", 2)

    response = _upload(make_client(make_user("alice")), "bai1.pdf", make_pdf(pages=3))

    assert response.status_code == 422
    assert "tối đa 2 trang" in response.json()["detail"]
    assert db_session.query(Document).count() == 0
    assert list(upload_dir.iterdir()) == []


def test_pdf_page_exceeding_pixel_budget_is_rejected(make_client, make_user, upload_dir, enqueued_jobs, make_pdf, monkeypatch):
    monkeypatch.setattr(upload_validation, "MAX_PAGE_PIXELS", 1_000_000)

    response = _upload(make_client(make_user("alice")), "bai1.pdf", make_pdf(size=(595, 842)))

    assert response.status_code == 422
    assert "Trang 1" in response.json()["detail"]
    assert list(upload_dir.iterdir()) == []


def test_pdf_at_the_pixel_budget_is_accepted(make_client, make_user, enqueued_jobs, make_pdf, monkeypatch):
    # A4 ở 150 dpi ≈ 2,2 triệu pixel: ngưỡng mặc định phải cho qua.
    response = _upload(make_client(make_user("alice")), "bai1.pdf", make_pdf(size=(595, 842)))

    assert response.status_code == 200


def test_oversized_upload_is_rejected_without_leaving_files(make_client, make_user, db_session, upload_dir, enqueued_jobs, make_pdf, monkeypatch):
    monkeypatch.setattr(documents_api, "MAX_FILE_SIZE", 100)

    response = _upload(make_client(make_user("alice")), "bai1.pdf", make_pdf(pages=5))

    assert response.status_code == 413
    assert db_session.query(Document).count() == 0
    assert list(upload_dir.iterdir()) == []


@pytest.mark.parametrize("name", ["bai1.png", "bai1.txt", "bai1", ".pdf", "bai1.pdf.exe"])
def test_non_pdf_extensions_are_rejected(make_client, make_user, upload_dir, enqueued_jobs, make_pdf, name):
    response = _upload(make_client(make_user("alice")), name, make_pdf())

    assert response.status_code == 400
    assert list(upload_dir.iterdir()) == []


def test_path_traversal_in_filename_cannot_escape_the_document_directory(
    make_client, make_user, db_session, upload_dir, enqueued_jobs, make_pdf
):
    response = _upload(make_client(make_user("alice")), "../../etc/passwd.pdf", make_pdf())

    assert response.status_code == 200
    document = _only_document(db_session)
    assert document.filename == "passwd.pdf"
    stored = sorted(path.relative_to(upload_dir).as_posix() for path in upload_dir.rglob("*") if path.is_file())
    assert stored == [f"{document.id}/source.pdf"]


def test_very_long_filename_is_truncated_but_keeps_the_pdf_extension(
    make_client, make_user, db_session, upload_dir, enqueued_jobs, make_pdf
):
    # Ký tự điều khiển được trình duyệt/httpx mã hóa %XX trong multipart nên không tới được server;
    # việc loại chúng được kiểm ở tests/unit/test_sanitize_filename.py.
    response = _upload(make_client(make_user("alice")), "a" * 400 + ".pdf", make_pdf())

    assert response.status_code == 200
    document = _only_document(db_session)
    assert len(document.filename) == 255 and document.filename.endswith(".pdf")