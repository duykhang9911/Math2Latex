from uuid import uuid4

import pytest

from app.models import Document, FormulaEntry


def _document(db, user, status="ocr_complete"):
    document = Document(id=uuid4(), filename="bai1.pdf", status=status, uploaded_by=user.id)
    db.add(document)
    db.commit()
    return document


def _formula(db, document, status="ocr_complete", latex_raw="x^2", latex_final=None):
    formula = FormulaEntry(
        id=uuid4(), document_id=document.id, page_number=1, status=status, latex_raw=latex_raw, latex_final=latex_final
    )
    db.add(formula)
    db.commit()
    return formula


def _submit(client, document, formula, latex_final):
    return client.post(
        f"/api/documents/{document.id}/formulas/{formula.id}/submit", json={"latex_final": latex_final}
    )


def _stored(db, formula):
    db.expire_all()
    return db.get(FormulaEntry, formula.id)


def test_submit_writes_latex_final_and_keeps_latex_raw(make_client, make_user, db_session):
    user = make_user("alice")
    document = _document(db_session, user)
    formula = _formula(db_session, document, latex_raw="x^{2")

    response = _submit(make_client(user), document, formula, "x^{2}")

    assert response.status_code == 200
    assert response.json() == {
        "formula_id": str(formula.id),
        "latex_raw": "x^{2",
        "latex_final": "x^{2}",
        "status": "submitted",
    }
    stored = _stored(db_session, formula)
    assert (stored.latex_raw, stored.latex_final, stored.status) == ("x^{2", "x^{2}", "submitted")


def test_resubmitting_updates_latex_final_again_and_never_touches_latex_raw(make_client, make_user, db_session):
    user = make_user("alice")
    document = _document(db_session, user)
    formula = _formula(db_session, document, latex_raw="original ocr")
    client = make_client(user)

    assert _submit(client, document, formula, "first").status_code == 200
    second = _submit(client, document, formula, "second")

    assert second.status_code == 200
    stored = _stored(db_session, formula)
    assert (stored.latex_raw, stored.latex_final, stored.status) == ("original ocr", "second", "submitted")


@pytest.mark.parametrize("status", ["proposed", "ocr_queued", "ocr_failed"])
def test_formula_that_has_not_been_recognized_cannot_be_submitted(make_client, make_user, db_session, status):
    user = make_user("alice")
    document = _document(db_session, user)
    formula = _formula(db_session, document, status=status, latex_raw=None)

    response = _submit(make_client(user), document, formula, "x")

    assert response.status_code == 409
    stored = _stored(db_session, formula)
    assert stored.latex_final is None and stored.status == status


def test_latex_final_length_limit(make_client, make_user, db_session):
    user = make_user("alice")
    document = _document(db_session, user)
    formula = _formula(db_session, document)
    client = make_client(user)

    assert _submit(client, document, formula, "a" * 100000).status_code == 200
    too_long = _submit(client, document, formula, "a" * 100001)

    assert too_long.status_code == 422
    assert len(_stored(db_session, formula).latex_final) == 100000


def test_submit_requires_a_json_body_with_latex_final(make_client, make_user, db_session):
    user = make_user("alice")
    document = _document(db_session, user)
    formula = _formula(db_session, document)

    response = make_client(user).post(f"/api/documents/{document.id}/formulas/{formula.id}/submit", json={})

    assert response.status_code == 422


def test_submit_is_scoped_to_the_owner_and_to_the_formulas_document(make_client, make_user, db_session):
    owner, other = make_user("alice"), make_user("bob")
    document, other_document = _document(db_session, owner), _document(db_session, other)
    formula = _formula(db_session, document)

    assert _submit(make_client(other), document, formula, "stolen").status_code == 404
    assert _submit(make_client(other), other_document, formula, "stolen").status_code == 404
    assert _submit(make_client(owner), document, type("F", (), {"id": uuid4()}), "x").status_code == 404
    assert _stored(db_session, formula).latex_final is None


def test_submit_requires_login(make_client, make_user, db_session):
    from fastapi.testclient import TestClient

    from app.main import app

    user = make_user("alice")
    document = _document(db_session, user)
    formula = _formula(db_session, document)

    response = _submit(TestClient(app), document, formula, "x")

    assert response.status_code == 401


def test_submit_is_logged_and_persists_across_reload(make_client, make_user, db_session, logged_actions):
    user = make_user("alice")
    document = _document(db_session, user)
    formula = _formula(db_session, document, latex_raw="raw")
    client = make_client(user)

    _submit(client, document, formula, "final")
    reloaded = client.get(f"/api/documents/{document.id}/formulas").json()["formulas"][0]

    assert (reloaded["latex_raw"], reloaded["latex_final"], reloaded["status"]) == ("raw", "final", "submitted")
    assert logged_actions == [
        {"action": "submit", "ref_id": formula.id, "detail": {"document_id": str(document.id)}, "user_id": user.id}
    ]
