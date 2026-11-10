# Backend guide

- `app/api/`: HTTP route, validation, mapping lỗi service → mã HTTP. `documents.py` (upload, lịch sử, tải/xuất, trang), `formulas.py` (vùng công thức, OCR, Submit), `auth.py`, `deps.py` (lấy document của owner).
- `app/core/`: cấu hình hạ tầng dùng chung: `database.py`, `queue.py` (RQ), `storage.py` (đường dẫn file), `limits.py` (giới hạn, đọc từ biến môi trường), `security.py` (password/JWT), `rate_limit.py` (giới hạn đăng nhập sai).
- `app/models/`: SQLAlchemy mappings; `status` của document/formula có CHECK constraint, danh sách giá trị nằm cạnh model.
- `app/schemas/`: Pydantic API contracts.
- `app/services/`: use case không phụ thuộc HTTP: render/detect/crop/OCR (`pdf_pages`, `formula_regions`, `formula_ocr`), hàng đợi OCR (`ocr_queue`), kiểm tra upload (`upload_validation`), xuất `.tex` (`latex_export`), truy vấn tóm tắt (`document_queries`), ghi log hành động (`action_log`), dọn thư mục mồ côi (`retention`).
- `alembic/versions/`: immutable schema history; create a new revision.
- `tests/`: `unit/`, `api/` (SQLite; vài test cần `TEST_PG_URL`/`TEST_REDIS_URL`), `worker/`. Cách chạy ở `tests/README.md`.

Keep model inference in RQ worker processes. Keep DB state canonical. Job functions need importable module paths and serializable arguments, và mọi job enqueue kèm `on_failure`. Validate upload, bbox and document/formula ownership in API. Test queue unavailable, duplicate enqueue, worker restart and model failure.

Patch điểm duy nhất khi test: `app.core.storage.UPLOAD_DIR`, `app.core.queue.enqueue_job`, `app.services.action_log.log_action`. Code gọi chúng qua module (`storage.…`, `queue.enqueue_job`, `action_log.log_action`) để một lần patch có hiệu lực toàn app.