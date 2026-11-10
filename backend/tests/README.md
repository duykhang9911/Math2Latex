# Backend tests

Cài `requirements-dev.txt` rồi chạy từ thư mục `backend/`:

```powershell
$env:DB_URL = "sqlite://"
$env:AUTH_SECRET = "unit-test-secret-that-is-long-enough-123456"
python -m pytest tests -q
```

Cấu trúc hiện có và đề xuất:

```text
tests/
|-- unit/          # security, bbox, status transitions, service behavior với fake model
|-- api/           # FastAPI route (SQLite in-memory, enqueue/log được thay bằng fake); test_ocr_queue_concurrency.py cần PostgreSQL (TEST_PG_URL)
|-- worker/        # job OCR/PDF với fake model, failure callback, job chạy trùng (SQLite); drill restart worker/Redis chạy thủ công, ghi ở ARCHITECTURE.md
`-- fixtures/      # chỉ dữ liệu synthetic hoặc PDF được phép dùng
```

`tests/api` dùng SQLite nên không kiểm tra được kiểu JSONB của `logs`, migration hay `SELECT ... FOR UPDATE`; migration cần chạy bằng `alembic upgrade head` trên PostgreSQL.

Test đồng thời cần PostgreSQL thật (`tests/api/test_ocr_queue_concurrency.py`, tự bỏ qua nếu thiếu `TEST_PG_URL`). Dùng database tạm, vì fixture xóa toàn bộ bảng sau mỗi test:

```powershell
docker compose exec db psql -U math2latex_user -d postgres -c "CREATE DATABASE m2l_test;"
docker compose exec backend sh -c "pip install -q -r requirements-dev.txt; TEST_PG_URL=postgresql://math2latex_user:math2latex_pass@db:5432/m2l_test DB_URL=sqlite:// AUTH_SECRET=unit-test-secret-that-is-long-enough-123456 python -m pytest tests -q"
docker compose exec db psql -U math2latex_user -d postgres -c "DROP DATABASE m2l_test;"
```

Image backend không cài pytest sẵn; lệnh `pip install` ở trên chỉ ảnh hưởng container đang chạy.

Không lưu PDF/crop cá nhân hoặc model weights trong fixtures. Test GPU/real model nên opt-in, không làm unit test mặc định phụ thuộc CUDA hoặc Internet.
