from pathlib import Path
from uuid import UUID, uuid4

import pytest
from PIL import Image

from app.models import Document, FormulaEntry

PAGE_SIZE = (200, 100)


def _ready_document(db, user, upload_dir, pages=1, status="formula_proposals_ready"):
    document = Document(id=uuid4(), filename="bai1.pdf", status=status, uploaded_by=user.id)
    db.add(document)
    db.commit()
    pages_dir = upload_dir / str(document.id) / "pages"
    pages_dir.mkdir(parents=True)
    for number in range(1, pages + 1):
        Image.new("RGB", PAGE_SIZE, "white").save(pages_dir / f"page-{number:06d}.png")
    return document


def _add_formula(db, document, upload_dir, status="proposed", bounds=(10, 10, 60, 40), page_number=1, **extra):
    formula_id = uuid4()
    crop = upload_dir / str(document.id) / "formulas" / f"{formula_id}.png"
    crop.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (bounds[2] - bounds[0], bounds[3] - bounds[1]), "white").save(crop)
    formula = FormulaEntry(
        id=formula_id,
        document_id=document.id,
        page_number=page_number,
        image_path=str(crop),
        x_min=bounds[0],
        y_min=bounds[1],
        x_max=bounds[2],
        y_max=bounds[3],
        status=status,
        **extra,
    )
    db.add(formula)
    db.commit()
    return formula


def _region(**overrides):
    return {"page_number": 1, "x_min": 10, "y_min": 20, "x_max": 110, "y_max": 70, **overrides}


# --- tạo vùng ------------------------------------------------------------------------------------------------


def test_create_region_saves_a_crop_that_matches_the_bounds(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)

    response = make_client(user).post(f"/api/documents/{document.id}/formulas", json=_region())

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["bounds"] == {"x_min": 10, "y_min": 20, "x_max": 110, "y_max": 70}
    assert body["status"] == "proposed" and body["latex_raw"] is None and body["latex_final"] is None
    formula = db_session.get(FormulaEntry, UUID(body["formula_id"]))
    with Image.open(formula.image_path) as crop:
        assert crop.size == (100, 50)
    assert formula.page_number == 1


def test_region_covering_the_whole_page_is_allowed(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)

    response = make_client(user).post(
        f"/api/documents/{document.id}/formulas", json=_region(x_min=0, y_min=0, x_max=200, y_max=100)
    )

    assert response.status_code == 201


@pytest.mark.parametrize(
    "overrides",
    [
        {"x_min": 50, "x_max": 50},
        {"x_min": 60, "x_max": 50},
        {"y_min": 40, "y_max": 40},
        {"y_min": 41, "y_max": 40},
        {"x_max": 201},
        {"y_max": 101},
    ],
    ids=["zero-width", "negative-width", "zero-height", "negative-height", "beyond-right", "beyond-bottom"],
)
def test_region_outside_or_empty_is_rejected_by_the_backend(make_client, make_user, db_session, upload_dir, overrides):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)

    response = make_client(user).post(f"/api/documents/{document.id}/formulas", json=_region(**overrides))

    assert response.status_code == 422
    assert db_session.query(FormulaEntry).count() == 0
    assert not (upload_dir / str(document.id) / "formulas").exists()


@pytest.mark.parametrize(
    "overrides",
    [{"page_number": 0}, {"x_min": -1}, {"y_min": -5}, {"x_max": 0}, {"y_max": 0}],
    ids=["page-zero", "negative-x", "negative-y", "zero-x-max", "zero-y-max"],
)
def test_schema_rejects_invalid_coordinates(make_client, make_user, db_session, upload_dir, overrides):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)

    response = make_client(user).post(f"/api/documents/{document.id}/formulas", json=_region(**overrides))

    assert response.status_code == 422


def test_page_numbers_start_at_one_and_unknown_pages_are_404(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir, pages=2)
    client = make_client(user)

    assert client.post(f"/api/documents/{document.id}/formulas", json=_region(page_number=2)).status_code == 201
    assert client.post(f"/api/documents/{document.id}/formulas", json=_region(page_number=3)).status_code == 404


def test_regions_can_only_be_added_while_proposals_are_ready(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir, status="ocr_processing")

    response = make_client(user).post(f"/api/documents/{document.id}/formulas", json=_region())

    assert response.status_code == 409


# --- sửa/xóa vùng ----------------------------------------------------------------------------------------------


def test_update_region_moves_the_bounds_and_regenerates_the_crop(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)
    formula = _add_formula(db_session, document, upload_dir)

    response = make_client(user).patch(
        f"/api/documents/{document.id}/formulas/{formula.id}",
        json={"x_min": 5, "y_min": 5, "x_max": 125, "y_max": 95},
    )

    assert response.status_code == 200, response.text
    db_session.expire_all()
    updated = db_session.get(FormulaEntry, formula.id)
    assert (updated.x_min, updated.y_min, updated.x_max, updated.y_max) == (5, 5, 125, 95)
    with Image.open(updated.image_path) as crop:
        assert crop.size == (120, 90)
    assert "v=5-5-125-95" in response.json()["image_url"]


def test_update_with_invalid_bounds_leaves_the_region_unchanged(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)
    formula = _add_formula(db_session, document, upload_dir)

    response = make_client(user).patch(
        f"/api/documents/{document.id}/formulas/{formula.id}",
        json={"x_min": 5, "y_min": 5, "x_max": 500, "y_max": 95},
    )

    assert response.status_code == 422
    db_session.expire_all()
    unchanged = db_session.get(FormulaEntry, formula.id)
    assert (unchanged.x_min, unchanged.y_min, unchanged.x_max, unchanged.y_max) == (10, 10, 60, 40)


@pytest.mark.parametrize("status", ["ocr_queued", "ocr_complete", "ocr_failed", "submitted"])
def test_only_proposed_regions_can_be_edited_or_deleted(make_client, make_user, db_session, upload_dir, status):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)
    formula = _add_formula(db_session, document, upload_dir, status=status)
    client = make_client(user)
    url = f"/api/documents/{document.id}/formulas/{formula.id}"

    assert client.patch(url, json={"x_min": 5, "y_min": 5, "x_max": 50, "y_max": 50}).status_code == 409
    assert client.delete(url).status_code == 409
    assert db_session.get(FormulaEntry, formula.id) is not None


def test_delete_region_removes_the_row_and_its_crop(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)
    formula = _add_formula(db_session, document, upload_dir)
    crop = formula.image_path

    response = make_client(user).delete(f"/api/documents/{document.id}/formulas/{formula.id}")

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(FormulaEntry, formula.id) is None
    assert not Path(crop).exists()


def test_region_routes_never_touch_another_users_or_documents_formulas(make_client, make_user, db_session, upload_dir):
    owner, other = make_user("alice"), make_user("bob")
    document = _ready_document(db_session, owner, upload_dir)
    formula = _add_formula(db_session, document, upload_dir)
    other_document = _ready_document(db_session, other, upload_dir)
    bob = make_client(other)
    region = {"x_min": 5, "y_min": 5, "x_max": 50, "y_max": 50}
    url = f"/api/documents/{document.id}/formulas"

    assert bob.get(url).status_code == 404
    assert bob.post(url, json=_region()).status_code == 404
    assert bob.patch(f"{url}/{formula.id}", json=region).status_code == 404
    assert bob.delete(f"{url}/{formula.id}").status_code == 404
    assert bob.get(f"{url}/{formula.id}/image").status_code == 404
    # công thức của document khác, dù người gọi sở hữu document trong URL
    assert bob.patch(f"/api/documents/{other_document.id}/formulas/{formula.id}", json=region).status_code == 404
    assert db_session.get(FormulaEntry, formula.id).x_min == 10


# --- danh sách, ảnh crop, trang -----------------------------------------------------------------------------------


def test_formula_list_is_ordered_by_page_and_exposes_raw_final_and_bounds(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir, pages=2, status="ocr_complete")
    second_page = _add_formula(db_session, document, upload_dir, status="ocr_complete", page_number=2, latex_raw="b")
    first_page = _add_formula(
        db_session, document, upload_dir, status="submitted", page_number=1, latex_raw="a", latex_final="a!"
    )

    body = make_client(user).get(f"/api/documents/{document.id}/formulas").json()

    assert body["status"] == "ocr_complete"
    assert [item["formula_id"] for item in body["formulas"]] == [str(first_page.id), str(second_page.id)]
    first = body["formulas"][0]
    assert (first["latex_raw"], first["latex_final"], first["status"]) == ("a", "a!", "submitted")
    assert first["bounds"] == {"x_min": 10, "y_min": 10, "x_max": 60, "y_max": 40}


def test_formula_image_is_served_and_404_when_the_file_is_gone(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir)
    formula = _add_formula(db_session, document, upload_dir)
    client = make_client(user)
    url = f"/api/documents/{document.id}/formulas/{formula.id}/image"

    ok = client.get(url)
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png"

    Path(formula.image_path).unlink()
    assert client.get(url).status_code == 404


def test_page_list_and_page_images(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = _ready_document(db_session, user, upload_dir, pages=2)
    client = make_client(user)

    pages = client.get(f"/api/documents/{document.id}/pages").json()["pages"]

    assert [(page["page_number"], page["width"], page["height"]) for page in pages] == [(1, 200, 100), (2, 200, 100)]
    assert pages[0]["image_url"] == f"/api/documents/{document.id}/pages/1"
    assert client.get(pages[1]["image_url"]).status_code == 200
    assert client.get(f"/api/documents/{document.id}/pages/0").status_code == 404
    assert client.get(f"/api/documents/{document.id}/pages/3").status_code == 404


def test_document_without_rendered_pages_returns_an_empty_page_list(make_client, make_user, db_session, upload_dir):
    user = make_user("alice")
    document = Document(id=uuid4(), filename="a.pdf", status="processing_pages", uploaded_by=user.id)
    db_session.add(document)
    db_session.commit()

    response = make_client(user).get(f"/api/documents/{document.id}/pages")

    assert response.status_code == 200 and response.json()["pages"] == []
