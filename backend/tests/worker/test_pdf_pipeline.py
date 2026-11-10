from uuid import uuid4

import pymupdf
import pytest
from PIL import Image

from app.models import Document, FormulaEntry
from app.services import formula_regions, pdf_pages



def _box(x_min, y_min, x_max, y_max):
    return [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]]


class FakeDetector:
    """Trả danh sách box cho từng lần gọi theo thứ tự trang; lỗi nếu phần tử là Exception."""

    def __init__(self, per_page):
        self.per_page = list(per_page)
        self.calls = 0

    def __call__(self, image_path, resized_shape=1024):
        result = self.per_page[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return [{"box": box, "score": score} for box, score in result]


@pytest.fixture()
def source_pdf(tmp_path):
    def _make(pages=2):
        path = tmp_path / "source.pdf"
        with pymupdf.open() as document:
            for _ in range(pages):
                document.new_page(width=595, height=842)
            document.save(path)
        return path

    return _make


def _processing_document(factory):
    with factory() as db:
        document = Document(id=uuid4(), filename="bai1.pdf", status="processing_pages")
        db.add(document)
        db.commit()
        return document.id


def _run(worker_db, monkeypatch, source_pdf, detector, pages=2):
    monkeypatch.setattr(formula_regions, "_load_detector", lambda: detector)
    document_id = _processing_document(worker_db)
    pdf_pages.process_pdf_pages(document_id, source_pdf(pages))
    with worker_db() as db:
        document = db.get(Document, document_id)
        formulas = db.query(FormulaEntry).filter(FormulaEntry.document_id == document_id).order_by(
            FormulaEntry.page_number, FormulaEntry.x_min
        ).all()
        return document, formulas


def test_pipeline_numbers_pages_from_one_and_stores_proposals(worker_db, monkeypatch, source_pdf, tmp_path):
    detector = FakeDetector([[(_box(100, 200, 300, 260), 0.9), (_box(400, 500, 700, 580), 0.7)], []])

    document, formulas = _run(worker_db, monkeypatch, source_pdf, detector)

    assert (document.status, document.page_count) == ("formula_proposals_ready", 2)
    assert [(formula.page_number, formula.status) for formula in formulas] == [(1, "proposed"), (1, "proposed")]
    assert [round(formula.confidence, 1) for formula in formulas] == [0.9, 0.7]
    assert sorted(path.name for path in (tmp_path / "pages").glob("*.png")) == ["page-000001.png", "page-000002.png"]
    assert all(formula.latex_raw is None and formula.latex_final is None for formula in formulas)


def test_pipeline_with_no_formulas_still_completes_with_an_empty_list(worker_db, monkeypatch, source_pdf):
    document, formulas = _run(worker_db, monkeypatch, source_pdf, FakeDetector([[], []]))

    assert document.status == "formula_proposals_ready"
    assert formulas == []


def test_bounds_are_clamped_to_the_page_and_the_crop_matches_the_bounds(worker_db, monkeypatch, source_pdf, tmp_path):
    detector = FakeDetector(
        [
            [
                (_box(-20, -10, 100, 50), 0.8),  # nhô ra trái/trên
                (_box(1200, 1700, 1400, 1900), 0.8),  # nhô ra phải/dưới
                (_box(2000, 100, 2100, 200), 0.8),  # hoàn toàn ngoài trang → bỏ
            ],
        ]
    )

    document, formulas = _run(worker_db, monkeypatch, source_pdf, detector, pages=1)

    with Image.open(tmp_path / "pages" / "page-000001.png") as page:
        page_width, page_height = page.size  # A4 ở 150 dpi, làm tròn lên theo PyMuPDF
    assert len(formulas) == 2
    for formula in formulas:
        assert 0 <= formula.x_min < formula.x_max <= page_width
        assert 0 <= formula.y_min < formula.y_max <= page_height
        with Image.open(formula.image_path) as crop:
            assert crop.size == (formula.x_max - formula.x_min, formula.y_max - formula.y_min)
    assert (formulas[0].x_min, formulas[0].y_min) == (0, 0)
    assert (formulas[1].x_max, formulas[1].y_max) == (page_width, page_height)


def test_detector_failure_fails_the_document_and_removes_partial_crops(worker_db, monkeypatch, source_pdf, tmp_path):
    detector = FakeDetector([[(_box(100, 200, 300, 260), 0.9)], RuntimeError("model crashed")])

    document, formulas = _run(worker_db, monkeypatch, source_pdf, detector)

    assert document.status == "processing_failed"
    assert formulas == []
    assert list((tmp_path / "formulas").glob("*.png")) == []
    assert (tmp_path / "source.pdf").is_file(), "PDF nguồn được giữ để người dùng tải/xóa"
