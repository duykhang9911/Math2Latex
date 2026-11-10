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
- Mọi job enqueue kèm `on_failure` (xem [ARCHITECTURE](ARCHITECTURE.md), mục Phục hồi job).

### Ma trận kiểm thử lỗi hàng đợi (cập nhật 2026-11-10)

"UI" chỉ là kết quả đọc code `frontend/src/App.jsx`; chưa kiểm bằng trình duyệt (việc của S4-04/S4-06).

| Tình huống | Hành vi mong đợi | Test/bằng chứng | UI |
|---|---|---|---|
| Redis down lúc upload | 503, document `processing_failed` | `test_upload_marks_document_failed_when_redis_is_down`; drill thật | `setMessage` hiện lỗi; nhãn "Xử lý thất bại" |
| Redis down lúc recognize/retry | 503, state hoàn tác, gọi lại được | `test_recognize_restores_state_…`, `test_retry_restores_failed_state_…` | `setMessage` hiện lỗi |
| Hai request recognize/retry cùng lúc | Một 202, một 409, một job | `test_second_recognize_…`, `test_retry_requeues_…`, `test_ocr_queue_concurrency.py` (PostgreSQL) | Nút khóa khi `busy` |
| Worker chết giữa OCR | `ocr_queued` → `ocr_failed`, document `ocr_completed_with_errors`, retry được | `test_ocr_failure_callback_…`; drill thật (kill worker) | Panel "Thử OCR lại" khi có công thức lỗi |
| OCR lỗi một công thức | Chỉ công thức đó `ocr_failed` | `test_missing_crop_fails_only_that_formula` | Như trên |
| Không nạp được model OCR | Mọi công thức đang chờ → `ocr_failed` | `test_model_load_failure_…` | Như trên |
| PDF hỏng | `processing_failed`, không tạo công thức | `test_pdf_job_marks_document_failed_for_a_corrupt_pdf` | Nhãn "Xử lý thất bại"; **chưa có nút thử lại/upload lại** |
| Job chạy trùng/lặp | No-op, không OCR lại, không tạo thêm công thức | `test_running_the_same_job_twice_…`, `test_job_skips_formula_finished_…`, `test_pdf_job_for_an_already_processed_…` | — |
| Redis restart khi job đang chờ | Job còn nguyên, worker xử lý sau | Drill thật (AOF) | Polling tiếp tục |
| Worker không chạy, job chờ | Document giữ `processing_*` cho tới khi có worker | Drill thật | **Chưa có thông báo quá hạn**: UI hiện "Đang…" vô hạn |
| Mất dữ liệu Redis (xóa volume) | Chưa phát hiện được | — | Document kẹt `ocr_processing`/`processing_pages` |

## Definition of Done

- Acceptance criteria đáp ứng.
- Test/build/lint liên quan qua; blocker được ghi rõ.
- Migration chạy trên clean DB và upgrade DB có dữ liệu.
- Redis down/worker restart/OCR exception có behavior được kiểm thử.
- Không có secret, upload, weights hoặc generated output trong Git.
- UI hỗ trợ keyboard/touch và có loading/error/save state.
- Docs và handoff khớp với code.