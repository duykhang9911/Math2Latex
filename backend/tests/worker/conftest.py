import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Document, FormulaEntry, User
from app.services import formula_ocr, pdf_pages


@pytest.fixture()
def worker_db(monkeypatch):
    """Session factory SQLite thay cho SessionLocal mà job RQ tự mở trong worker."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__, Document.__table__, FormulaEntry.__table__])
    factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(formula_ocr, "SessionLocal", factory)
    monkeypatch.setattr(pdf_pages, "SessionLocal", factory)
    yield factory
    engine.dispose()
