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
|-- api/           # FastAPI route (SQLite in-memory, enqueue/log được thay bằng fake); chưa có test PostgreSQL thật
|-- worker/        # (chưa có) RQ enqueue, retries, failure/restart behavior
`-- fixtures/      # chỉ dữ liệu synthetic hoặc PDF được phép dùng
```

`tests/api` dùng SQLite nên không kiểm tra được kiểu JSONB của `logs` hay migration; migration cần chạy bằng `alembic upgrade head` trên PostgreSQL.

Không lưu PDF/crop cá nhân hoặc model weights trong fixtures. Test GPU/real model nên opt-in, không làm unit test mặc định phụ thuộc CUDA hoặc Internet.
