from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Document, FormulaEntry
from app.models.document import DOCUMENT_STATUSES
from app.models.formula_entry import FORMULA_STATUSES


@pytest.mark.parametrize("status", DOCUMENT_STATUSES)
def test_document_accepts_every_known_status(db_session, status):
    db_session.add(Document(id=uuid4(), filename="a.pdf", status=status))
    db_session.commit()


def test_document_rejects_unknown_status(db_session):
    db_session.add(Document(id=uuid4(), filename="a.pdf", status="done"))

    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize("status", FORMULA_STATUSES)
def test_formula_accepts_every_known_status(db_session, status):
    document = Document(id=uuid4(), filename="a.pdf", status="ocr_complete")
    db_session.add(document)
    db_session.commit()
    db_session.add(FormulaEntry(id=uuid4(), document_id=document.id, status=status))
    db_session.commit()


def test_formula_rejects_unknown_status(db_session):
    document = Document(id=uuid4(), filename="a.pdf", status="ocr_complete")
    db_session.add(document)
    db_session.commit()
    db_session.add(FormulaEntry(id=uuid4(), document_id=document.id, status="edited"))

    with pytest.raises(IntegrityError):
        db_session.commit()
