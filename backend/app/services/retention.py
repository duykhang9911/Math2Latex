"""Dọn thư mục upload mồ côi.

Chính sách (xem Docs/DATABASE.md, mục Retention):
- Chỉ xóa thư mục con trực tiếp của UPLOAD_DIR có tên là UUID, KHÔNG có dòng `documents` tương ứng và
  cũ hơn `--min-age-hours` (mặc định 24 giờ; upload đang ghi file có thư mục trước khi có dòng database).
- Không bao giờ xóa document, dòng database hay thư mục của document đang tồn tại — kể cả document thất bại
  hoặc chưa có owner. Người dùng tự xóa document qua lịch sử.
- Mặc định chỉ liệt kê (dry-run); phải truyền `--apply` mới xóa.

    docker compose exec backend python -m app.services.retention [--apply] [--min-age-hours 24]
"""
import argparse
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Document

logger = logging.getLogger(__name__)


@dataclass
class RetentionReport:
    orphan_directories: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    documents_missing_files: list[UUID] = field(default_factory=list)


def _uuid_directories(upload_dir: Path) -> dict[UUID, Path]:
    directories = {}
    for entry in upload_dir.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue
        try:
            document_id = UUID(entry.name)
        except ValueError:
            continue
        if str(document_id) == entry.name:
            directories[document_id] = entry
    return directories


def cleanup_orphan_directories(
    db: Session,
    upload_dir: Path,
    min_age_seconds: float = 24 * 3600,
    apply: bool = False,
    now: float | None = None,
) -> RetentionReport:
    now = time.time() if now is None else now
    report = RetentionReport()
    directories = _uuid_directories(upload_dir)
    known_ids = {row[0] for row in db.query(Document.id).all()}

    for document_id, directory in sorted(directories.items(), key=lambda item: str(item[0])):
        if document_id in known_ids:
            continue
        if now - directory.stat().st_mtime < min_age_seconds:
            continue
        report.orphan_directories.append(directory)
        if apply:
            shutil.rmtree(directory)
            report.deleted.append(directory)
            logger.info("Removed orphan upload directory %s", directory)

    report.documents_missing_files = sorted(known_ids - set(directories), key=str)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dọn thư mục upload không có dòng documents tương ứng.")
    parser.add_argument("--apply", action="store_true", help="Xóa thật; mặc định chỉ liệt kê")
    parser.add_argument("--min-age-hours", type=float, default=24, help="Chỉ xóa thư mục cũ hơn số giờ này")
    args = parser.parse_args(argv)

    from app.core.database import SessionLocal

    upload_dir = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
    with SessionLocal() as db:
        report = cleanup_orphan_directories(
            db, upload_dir, min_age_seconds=args.min_age_hours * 3600, apply=args.apply
        )

    action = "Đã xóa" if args.apply else "Sẽ xóa (dry-run, thêm --apply để xóa thật)"
    print(f"{action}: {len(report.orphan_directories)} thư mục mồ côi")
    for directory in report.orphan_directories:
        print(f"  {directory}")
    print(f"Document không còn thư mục file (không bị đụng tới): {len(report.documents_missing_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
