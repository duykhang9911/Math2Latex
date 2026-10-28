# Database và persistence

## Bảng hiện có

| Bảng | Vai trò | Trường tiêu biểu |
|---|---|---|
| `users` | Tài khoản local | `id`, `username` unique, `password_hash`, `created_at` |
| `documents` | Tài liệu upload | `id`, `filename`, `status`, `uploaded_by`, `created_at` |
| `formula_entries` | Mỗi vùng/công thức | `document_id`, `page_number`, `image_path`, bbox, `confidence`, `latex_raw`, `latex_final`, `ocr_backend`, `status` |
| `logs` | Khung event log; chưa gắn toàn bộ API | `action`, `ref_id`, JSONB `detail` |

`formula_entries.document_id` là foreign key tới `documents.id`. File PDF/page/crop nằm filesystem; database chứa metadata và đường dẫn.

## Migration

- `1c603257d451_create_initial_tables.py`: tạo bảng ban đầu.
- `7fd904b9f5b1_add_formula_region_bounds.py`: thêm bbox và confidence.
- `a6b0f1c2d3e4_add_user_ownership_foreign_key.py`: nối `documents.uploaded_by` tới `users.id`, nullable và `ON DELETE SET NULL`.
- Luôn tạo revision mới; không chỉnh revision đã áp dụng.

```powershell
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

## Quy tắc

- `latex_raw` giữ output OCR; không sửa khi người dùng Submit.
- `latex_final` là nội dung người dùng xác nhận.
- Bbox lưu tọa độ pixel của ảnh đã render, không phải PDF points.
- `status` transition cần validate; các enqueue/retry concurrent cần khóa/idempotency.
- `image_path` chỉ do backend tạo; không nhận filesystem path từ client.
- Username được chuẩn hóa lowercase trước khi lưu; unique constraint ở database vẫn là chốt chống trùng cuối cùng.
- Password hash là Argon2; tuyệt đối không lưu plaintext.
- Document cũ có `uploaded_by IS NULL` không tự gán cho tài khoản đầu tiên; cần quy trình quản trị riêng nếu muốn chuyển owner.
- Mỗi migration cần kiểm tra upgrade từ revision hiện có và từ database rỗng.

## PostgreSQL và Redis

PostgreSQL là nguồn canonical của document/formula. Redis/RQ lưu job lifecycle/result/failure; Redis không thay DB. Redis AOF và `redisdata` volume được khai báo; cần kiểm thử restore/retry khi worker/API restart.