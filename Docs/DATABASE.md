# Database và persistence

## Bảng hiện có

| Bảng | Vai trò | Trường tiêu biểu |
|---|---|---|
| `users` | Tài khoản local | `id`, `username` unique, `password_hash`, `created_at` |
| `documents` | Tài liệu upload; cũng là nguồn của lịch sử tải lên | `id`, `filename`, `status`, `uploaded_by`, `file_size_bytes`, `page_count`, `created_at`, `updated_at` |
| `formula_entries` | Mỗi vùng/công thức | `document_id`, `page_number`, `image_path`, bbox, `confidence`, `latex_raw`, `latex_final`, `ocr_backend`, `status` |
| `logs` | Event log của API upload/OCR/lịch sử | `action`, `ref_id`, `user_id` (nullable), JSONB `detail` |

`formula_entries.document_id` là foreign key tới `documents.id` (không có `ON DELETE CASCADE`; API xóa lịch sử phải xóa công thức trước). File PDF/page/crop nằm filesystem; database chứa metadata và đường dẫn.

## Lịch sử tải lên

- Lịch sử của user = các `documents` có `uploaded_by = user.id`, sắp xếp `created_at DESC`; index `ix_documents_uploaded_by_created_at`. Document `uploaded_by IS NULL` không hiện cho ai.
- `file_size_bytes` ghi lúc upload; `page_count` ghi khi worker render xong PDF; `updated_at` tự cập nhật mỗi lần ORM update. Document tạo trước migration `b7c1d2e3f4a5` có `file_size_bytes`/`page_count` NULL.
- `formula_count`/`submitted_count` không lưu cột, tính bằng aggregate trên `formula_entries` khi list.
- Xóa một mục lịch sử xóa `formula_entries`, row `documents` rồi thư mục `UPLOAD_DIR/{id}`; không cho xóa khi status là `processing_pages`, `detecting_formulas`, `ocr_processing`.
- Action log của lịch sử: `history_list`, `history_open`, `history_delete`, `download_source`, `export_latex`; kèm `logs.user_id`.

## Migration

- `1c603257d451_create_initial_tables.py`: tạo bảng ban đầu.
- `7fd904b9f5b1_add_formula_region_bounds.py`: thêm bbox và confidence.
- `a6b0f1c2d3e4_add_user_ownership_foreign_key.py`: nối `documents.uploaded_by` tới `users.id`, nullable và `ON DELETE SET NULL`.
- `b7c1d2e3f4a5_add_document_history_columns.py`: thêm `documents.file_size_bytes/page_count/updated_at` (backfill `updated_at = created_at`), index lịch sử và `logs.user_id` (FK `ON DELETE SET NULL`).
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