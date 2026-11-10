from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image

from app.models import Document, FormulaEntry
from app.services import formula_ocr, pdf_pages


class FakeOcrModel:
    def __init__(self, latex="x^2"):
        self.latex = latex
        self.calls = 0

    def __call__(self, image):
        self.calls += 1
        return self.latex


@pytest.fixture()
def fake_model(monkeypatch):
    model = FakeOcrModel()
    monkeypatch.setattr(formula_ocr, "_load_ocr_model", lambda: model)
    return model


def _add_document(factory, status="ocr_processing"):
    with factory() as db:
        document = Document(id=uuid4(), filename="bai1.pdf", status=status)
        db.add(document)
        db.commit()
        return document.id


def _add_formula(factory, document_id, tmp_path, status="ocr_queued", crop=True, **extra):
    formula_id = uuid4()
    image_path = tmp_path / f"{formula_id}.png"
    if crop:
        Image.new("RGB", (20, 10), "white").save(image_path)
    with factory() as db:
        db.add(
            FormulaEntry(
                id=formula_id,
                document_id=document_id,
                page_number=1,
                image_path=str(image_path),
                status=status,
                **extra,
            )
        )
        db.commit()
    return formula_id


def _formula(factory, formula_id):
    with factory() as db:
        return db.get(FormulaEntry, formula_id)


def _document_status(factory, document_id):
    with factory() as db:
        return db.get(Document, document_id).status


def test_ocr_job_completes_queued_formulas(worker_db, fake_model, tmp_path):
    document_id = _add_document(worker_db)
    ids = [_add_formula(worker_db, document_id, tmp_path) for _ in range(2)]

    formula_ocr.process_formula_ocr(document_id)

    for formula_id in ids:
        formula = _formula(worker_db, formula_id)
        assert (formula.status, formula.latex_raw, formula.ocr_backend) == ("ocr_complete", "x^2", "pix2tex")
        assert formula.latex_final is None
    assert _document_status(worker_db, document_id) == "ocr_complete"


def test_missing_crop_fails_only_that_formula(worker_db, fake_model, tmp_path):
    document_id = _add_document(worker_db)
    good = _add_formula(worker_db, document_id, tmp_path)
    bad = _add_formula(worker_db, document_id, tmp_path, crop=False)

    formula_ocr.process_formula_ocr(document_id)

    assert _formula(worker_db, good).status == "ocr_complete"
    assert _formula(worker_db, bad).status == "ocr_failed"
    assert _document_status(worker_db, document_id) == "ocr_completed_with_errors"


def test_model_load_failure_marks_every_queued_formula_failed(worker_db, tmp_path, monkeypatch):
    def _broken_model():
        raise RuntimeError("weights missing")

    monkeypatch.setattr(formula_ocr, "_load_ocr_model", _broken_model)
    document_id = _add_document(worker_db)
    ids = [_add_formula(worker_db, document_id, tmp_path) for _ in range(2)]

    formula_ocr.process_formula_ocr(document_id)

    assert [_formula(worker_db, formula_id).status for formula_id in ids] == ["ocr_failed", "ocr_failed"]
    assert _document_status(worker_db, document_id) == "ocr_completed_with_errors"


def test_job_never_touches_formulas_that_are_not_queued(worker_db, fake_model, tmp_path):
    document_id = _add_document(worker_db)
    queued = _add_formula(worker_db, document_id, tmp_path)
    submitted = _add_formula(
        worker_db, document_id, tmp_path, status="submitted", latex_raw="old raw", latex_final="user final"
    )
    proposed = _add_formula(worker_db, document_id, tmp_path, status="proposed")

    formula_ocr.process_formula_ocr(document_id)

    assert _formula(worker_db, queued).status == "ocr_complete"
    kept = _formula(worker_db, submitted)
    assert (kept.status, kept.latex_raw, kept.latex_final) == ("submitted", "old raw", "user final")
    assert _formula(worker_db, proposed).status == "proposed"
    assert fake_model.calls == 1


def test_running_the_same_job_twice_does_not_redo_ocr(worker_db, fake_model, tmp_path):
    document_id = _add_document(worker_db)
    for _ in range(3):
        _add_formula(worker_db, document_id, tmp_path)

    formula_ocr.process_formula_ocr(document_id)
    formula_ocr.process_formula_ocr(document_id)

    assert fake_model.calls == 3
    assert _document_status(worker_db, document_id) == "ocr_complete"


def test_job_skips_formula_finished_by_a_concurrent_job(worker_db, tmp_path, monkeypatch):
    document_id = _add_document(worker_db)
    first = _add_formula(worker_db, document_id, tmp_path)
    second = _add_formula(worker_db, document_id, tmp_path)

    class RacingModel(FakeOcrModel):
        def __call__(self, image):
            if self.calls == 0:
                # Job khác hoàn tất công thức còn lại trong lúc job này đang chạy.
                with worker_db() as other:
                    other_formula = other.get(FormulaEntry, order[1])
                    other_formula.status, other_formula.latex_raw = "ocr_complete", "from other job"
                    other.commit()
            return super().__call__(image)

    model = RacingModel()
    monkeypatch.setattr(formula_ocr, "_load_ocr_model", lambda: model)
    with worker_db() as db:
        order = [
            formula.id
            for formula in db.query(FormulaEntry)
            .filter(FormulaEntry.document_id == document_id)
            .order_by(FormulaEntry.page_number, FormulaEntry.created_at)
        ]

    formula_ocr.process_formula_ocr(document_id)

    assert model.calls == 1
    assert _formula(worker_db, order[1]).latex_raw == "from other job"
    assert {first, second} == set(order)


def test_ocr_failure_callback_fails_only_queued_formulas(worker_db, tmp_path):
    document_id = _add_document(worker_db)
    queued = _add_formula(worker_db, document_id, tmp_path)
    done = _add_formula(worker_db, document_id, tmp_path, status="ocr_complete", latex_raw="x")
    submitted = _add_formula(worker_db, document_id, tmp_path, status="submitted", latex_final="y")

    formula_ocr.mark_ocr_job_failed(SimpleNamespace(args=(document_id,), id="job-1"), None, None, None, None)

    assert _formula(worker_db, queued).status == "ocr_failed"
    assert _formula(worker_db, done).status == "ocr_complete"
    assert _formula(worker_db, submitted).status == "submitted"
    assert _document_status(worker_db, document_id) == "ocr_completed_with_errors"


def test_ocr_failure_callback_keeps_document_status_when_not_processing(worker_db, tmp_path):
    document_id = _add_document(worker_db, status="ocr_complete")
    done = _add_formula(worker_db, document_id, tmp_path, status="ocr_complete")

    formula_ocr.mark_ocr_job_failed(SimpleNamespace(args=(document_id,), id="job-1"), None, None, None, None)

    assert _formula(worker_db, done).status == "ocr_complete"
    assert _document_status(worker_db, document_id) == "ocr_complete"


def test_failure_callbacks_ignore_a_deleted_document(worker_db):
    job = SimpleNamespace(args=(uuid4(),), id="job-1")

    formula_ocr.mark_ocr_job_failed(job, None, None, None, None)
    pdf_pages.mark_pdf_job_failed(job, None, None, None, None)


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("processing_pages", "processing_failed"),
        ("detecting_formulas", "processing_failed"),
        ("formula_proposals_ready", "formula_proposals_ready"),
        ("ocr_complete", "ocr_complete"),
    ],
)
def test_pdf_failure_callback_only_changes_documents_still_processing(worker_db, before, after):
    document_id = _add_document(worker_db, status=before)

    pdf_pages.mark_pdf_job_failed(SimpleNamespace(args=(document_id, "x.pdf"), id="job-1"), None, None, None, None)

    assert _document_status(worker_db, document_id) == after


def test_pdf_job_for_an_already_processed_document_is_a_noop(worker_db, tmp_path):
    document_id = _add_document(worker_db, status="ocr_complete")

    pdf_pages.process_pdf_pages(document_id, tmp_path / "missing.pdf")

    assert _document_status(worker_db, document_id) == "ocr_complete"
    with worker_db() as db:
        assert db.query(FormulaEntry).count() == 0


def test_pdf_job_marks_document_failed_for_a_corrupt_pdf(worker_db, tmp_path):
    document_id = _add_document(worker_db, status="processing_pages")
    broken = tmp_path / "source.pdf"
    broken.write_bytes(b"this is not a pdf")

    pdf_pages.process_pdf_pages(document_id, broken)

    assert _document_status(worker_db, document_id) == "processing_failed"
    with worker_db() as db:
        assert db.query(FormulaEntry).count() == 0

def test_pdf_job_refuses_a_file_over_the_page_limit(worker_db, tmp_path, monkeypatch):
    import pymupdf

    from app.services import upload_validation

    monkeypatch.setattr(upload_validation, "MAX_PDF_PAGES", 2)
    source = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        for _ in range(3):
            document.new_page()
        document.save(source)
    document_id = _add_document(worker_db, status="processing_pages")

    pdf_pages.process_pdf_pages(document_id, source)

    assert _document_status(worker_db, document_id) == "processing_failed"
    assert not (tmp_path / "pages").exists()
