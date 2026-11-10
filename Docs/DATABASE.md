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

## Database được dùng để làm gì trong dự án?

PostgreSQL là nguồn lưu trữ chính thức cho thông tin cần truy vấn và giữ lại giữa các phiên chạy:

1. `users` giữ username và password hash Argon2 để biết ai đang đăng nhập; không lưu mật khẩu rõ.
2. `documents` ghi tên, owner và trạng thái PDF để người dùng xem lại lịch sử, đồng thời giới hạn truy cập theo tài khoản.
3. `formula_entries` ghi trang, bbox, confidence, crop path, OCR gốc `latex_raw`, bản người dùng Submit `latex_final` và trạng thái từng công thức.
4. Foreign key/unique constraint bảo vệ quan hệ và chống username trùng; transaction giúp không để trạng thái nửa chừng khi cập nhật lỗi.
5. Khi mở lại trình duyệt, frontend lấy document/formula từ PostgreSQL qua API thay vì dựa vào state trong RAM.

PDF, page images và formula crops nằm trong `backend/uploads/`; Redis/RQ chỉ điều phối job nền. PostgreSQL không chứa ảnh/PDF và Redis không thay thế dữ liệu canonical trong PostgreSQL.

## Migration

- `1c603257d451_create_initial_tables.py`: tạo bảng ban đầu.
- `7fd904b9f5b1_add_formula_region_bounds.py`: thêm bbox và confidence.
- `a6b0f1c2d3e4_add_user_ownership_foreign_key.py`: nối `documents.uploaded_by` tới `users.id`, nullable và `ON DELETE SET NULL`.
- `b7c1d2e3f4a5_add_document_history_columns.py`: thêm `documents.file_size_bytes/page_count/updated_at` (backfill `updated_at = created_at`), index lịch sử và `logs.user_id` (FK `ON DELETE SET NULL`).
- `c8d2e3f4a5b6_add_status_check_constraints.py`: CHECK constraint `ck_documents_status` và `ck_formula_entries_status` (giá trị hợp lệ nằm ở `DOCUMENT_STATUSES`/`FORMULA_STATUSES` trong model và được chép cố định vào revision). Dùng CHECK thay vì enum của PostgreSQL vì thêm trạng thái chỉ cần migration mới, không cần `ALTER TYPE`. Đã chạy thử trên bản khôi phục từ dump dữ liệu thật: upgrade, downgrade, upgrade lại, và DB từ chối giá trị lạ.
- Luôn tạo revision mới; không chỉnh revision đã áp dụng.
- Kiểm thử ngày 2026-11-10 trên database tạm (đã xóa): `upgrade head` từ DB rỗng, `downgrade base`, `upgrade head` lại đều chạy hết 4 revision; với DB giữ một document ở revision `7fd904b9f5b1`, `upgrade head` giữ nguyên dòng cũ, `uploaded_by`/`file_size_bytes`/`page_count` là NULL và `updated_at` được backfill từ `created_at`.

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

## Retention và dọn dẹp

- Không có hạn dùng tự động cho document: dữ liệu của người dùng chỉ mất khi họ xóa ở lịch sử (API xóa cả dòng database lẫn `UPLOAD_DIR/<id>`), kể cả document thất bại hoặc chưa có owner.
- Render/detect thất bại: worker xóa crop dở dang; file PDF nguồn và document vẫn còn để người dùng tải/xóa.
- Thư mục mồ côi (có tên UUID nhưng không có dòng `documents`, ví dụ upload bị ngắt giữa chừng): `docker compose exec backend python -m app.services.retention` liệt kê (dry-run); thêm `--apply` để xóa; `--min-age-hours` (mặc định 24) bảo vệ upload đang ghi. Lệnh không bao giờ xóa document hoặc thư mục của document còn tồn tại, không đụng tới tên không phải UUID.
- Job lỗi trong Redis: RQ giữ 7 ngày (`failure_ttl`), kết quả 24 giờ.
- Trước khi dọn dẹp hay chạy `docker compose down -v`, sao lưu theo [DATASET](DATASET.md).

## Chuyển owner cho document cũ (`uploaded_by IS NULL`)

Mặc định (D-07) các document này không hiện cho ai. Muốn gán cho một tài khoản (ví dụ để dữ liệu đánh giá hiện trong lịch sử), làm thủ công sau khi sao lưu:

```powershell
docker compose exec db psql -U math2latex_user -d math2latex
```

```sql
BEGIN;
SELECT id, filename, status, created_at FROM documents WHERE uploaded_by IS NULL ORDER BY created_at;
UPDATE documents
   SET uploaded_by = (SELECT id FROM users WHERE username = 'ten_dang_nhap')
 WHERE uploaded_by IS NULL AND id IN ('<document_id>', '<document_id>');
-- kiểm tra số dòng bị đổi rồi COMMIT; hoặc ROLLBACK nếu sai
COMMIT;
```

Không có endpoint hay UI cho việc này: chuyển owner là thao tác quản trị, chỉ làm khi cần và chỉ với `document_id` đã liệt kê rõ; không dùng `UPDATE` không có `WHERE id IN (...)`.

## PostgreSQL và Redis

PostgreSQL là nguồn canonical của document/formula. Redis/RQ lưu job lifecycle/result/failure; Redis không thay DB. Redis AOF và `redisdata` volume được khai báo; cần kiểm thử restore/retry khi worker/API restart.