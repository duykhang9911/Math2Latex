# Quy trình phát triển feature

## Vertical slice

1. Gắn task với FR/acceptance criterion, actor và status transition.
2. Chốt request/response, ownership, bbox/raw/final contract.
3. Nếu đổi DB: Alembic revision mới.
4. Viết service/job callable riêng, có thể gọi từ RQ worker.
5. API validate, commit transition và enqueue; nếu Redis lỗi, khôi phục state hoặc báo lỗi retryable.
6. Frontend xử lý queued/loading/success/failure/unsaved/retry.
7. Thêm test đúng phạm vi: unit, API/DB/queue hoặc browser.
8. Cập nhật SRS/architecture/setup/backlog nếu contract/config/behavior đổi.

## Queue safety

- Không chạy inference trong HTTP handler.
- Chống double enqueue bằng row lock/idempotency.
- Job phải retry-safe; không tạo duplicate FormulaEntry/crop.
- Có timeout/retry/failure visibility và cách phục hồi `ocr_queued` bị treo.
- PostgreSQL giữ canonical status; RQ giữ job operational metadata.

## Definition of Done

- Acceptance criteria đáp ứng.
- Test/build/lint liên quan qua; blocker được ghi rõ.
- Migration chạy trên clean DB và upgrade DB có dữ liệu.
- Redis down/worker restart/OCR exception có behavior được kiểm thử.
- Không có secret, upload, weights hoặc generated output trong Git.
- UI hỗ trợ keyboard/touch và có loading/error/save state.
- Docs và handoff khớp với code.