import os
import time
from uuid import uuid4

from app.models import Document
from app.services.retention import cleanup_orphan_directories

DAY = 24 * 3600


def _make_dir(upload_dir, name, age_seconds=0, files=("source.pdf",)):
    directory = upload_dir / name
    directory.mkdir()
    for file_name in files:
        (directory / file_name).write_bytes(b"x")
    old = time.time() - age_seconds
    os.utime(directory, (old, old))
    return directory


def _add_document(db, document_id, uploaded_by=None, status="ocr_complete"):
    db.add(Document(id=document_id, filename="a.pdf", status=status, uploaded_by=uploaded_by))
    db.commit()


def test_dry_run_lists_old_orphans_but_deletes_nothing(db_session, tmp_path):
    orphan = _make_dir(tmp_path, str(uuid4()), age_seconds=3 * DAY)

    report = cleanup_orphan_directories(db_session, tmp_path)

    assert report.orphan_directories == [orphan]
    assert report.deleted == []
    assert orphan.exists()


def test_apply_removes_only_old_directories_without_a_document_row(db_session, tmp_path):
    kept_id, dataset_id, failed_id = uuid4(), uuid4(), uuid4()
    _add_document(db_session, kept_id)
    _add_document(db_session, dataset_id, uploaded_by=None)  # document dữ liệu chưa có owner
    _add_document(db_session, failed_id, status="processing_failed")
    keep = [_make_dir(tmp_path, str(document_id), age_seconds=30 * DAY) for document_id in (kept_id, dataset_id, failed_id)]
    recent_orphan = _make_dir(tmp_path, str(uuid4()), age_seconds=60)
    not_a_document = _make_dir(tmp_path, "backup-2026", age_seconds=30 * DAY)
    (tmp_path / ".gitkeep").write_text("")
    old_orphan = _make_dir(tmp_path, str(uuid4()), age_seconds=2 * DAY, files=("source.pdf", "pages-note.txt"))

    report = cleanup_orphan_directories(db_session, tmp_path, apply=True)

    assert report.deleted == [old_orphan]
    assert not old_orphan.exists()
    assert all(directory.exists() for directory in keep)
    assert recent_orphan.exists(), "thư mục mới có thể là upload đang ghi"
    assert not_a_document.exists(), "chỉ động tới thư mục có tên UUID"
    assert (tmp_path / ".gitkeep").exists()


def test_uppercase_or_malformed_uuid_names_are_left_alone(db_session, tmp_path):
    upper = _make_dir(tmp_path, str(uuid4()).upper(), age_seconds=30 * DAY)
    short = _make_dir(tmp_path, "1234", age_seconds=30 * DAY)

    report = cleanup_orphan_directories(db_session, tmp_path, apply=True)

    assert report.deleted == []
    assert upper.exists() and short.exists()


def test_reports_documents_whose_files_are_missing_without_touching_them(db_session, tmp_path):
    document_id = uuid4()
    _add_document(db_session, document_id)

    report = cleanup_orphan_directories(db_session, tmp_path, apply=True)

    assert report.documents_missing_files == [document_id]
    assert db_session.get(Document, document_id) is not None


def test_min_age_is_configurable(db_session, tmp_path):
    orphan = _make_dir(tmp_path, str(uuid4()), age_seconds=2 * 3600)

    assert cleanup_orphan_directories(db_session, tmp_path, min_age_seconds=3 * 3600).orphan_directories == []
    assert cleanup_orphan_directories(db_session, tmp_path, min_age_seconds=3600).orphan_directories == [orphan]
