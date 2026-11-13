# Ma trận truy vết yêu cầu — Math2Latex (S6-03)

> **Cập nhật:** 2026-11-13 — sau khi hoàn thành S4-01..S4-04, S4-10, S5-01..S5-03

Ma trận này truy vết từ yêu cầu SRS (FR/NFR) → module mã nguồn → test tự động/thủ công → trạng thái.

## Chú thích

- ✅ = có test tự động pass
- 🟡 = có test nhưng thiếu dữ liệu/chưa chạy end-to-end
- ⬜ = chưa có test tự động, chỉ kiểm thủ công
- ❌ = chưa có test nào

## FR0 — Đăng ký / Đăng nhập / Đăng xuất

| ID | Yêu cầu | Code | Backend test | Frontend test | Trạng thái |
|---|---|---|---|---|---|
| FR0-01 | Đăng ký/đăng nhập | `api/auth.py`, `schemas/auth.py` | `test_register_login_logout_and_password_hash` | `DocumentFlow.test: auth (4 tests)` | ✅ |
| FR0-02 | Argon2 hash, không lộ password | `core/security.py` | `test_passwords_and_tokens_are_never_logged` | — | ✅ |
| FR0-03 | JWT cookie, hardening | `core/security.py`, `api/auth.py` | `test_auth_hardening.py` (10+ tests) | — | ✅ |
| FR0-04 | Đăng xuất | `api/auth.py` | Logout → `/me` 401 | `DocumentFlow.test: logout (1 test)` | ✅ |
| FR0-05 | Owner scoping | `api/documents.py` | `test_document_is_visible_only_to_owner` (3 tests) | — | ✅ |

## FR1 — Upload PDF → Detect → OCR

| ID | Yêu cầu | Code | Backend test | Frontend test | Trạng thái |
|---|---|---|---|---|---|
| FR1-01 | Upload PDF | `api/documents.py` | `test_upload_records_size`, `test_upload_validation.py` | `DocumentFlow.test: upload (2 tests)` | ✅ |
| FR1-02 | Queue job | `core/queue.py` | `test_ocr_queue.py`, `test_ocr_queue_concurrency.py` | — | ✅ |
| FR1-03 | Render trang + detect bbox | `services/pdf_pages.py`, `formula_regions.py` | `test_pdf_pipeline.py` | — | ✅ |
| FR1-04 | Crop theo bbox | `models/formula_entry.py` | `test_formula_regions.py` (bbox trong ảnh, crop đúng) | — | ✅ |
| FR1-05 | Sửa vùng (tạo/sửa/xóa) | `api/formulas.py` | `test_formula_regions.py` (CRUD, bounds, owner) | `RegionOverlay.test: pointer events, keyboard` | ✅ |
| FR1-06 | OCR `latex_raw` | `services/formula_ocr.py` | `tests/worker/` (fake model) | — | ✅ |

## FR2 — Sửa LaTeX ↔ MathLive

| ID | Yêu cầu | Code | Backend test | Frontend test | Trạng thái |
|---|---|---|---|---|---|
| FR2-01 | UI review công thức | `App.jsx`, `FormulaEditor.jsx` | — | `FormulaEditor.test: render & display (4 tests)` | ✅ |
| FR2-02 | LaTeX ↔ MathLive sync | `FormulaEditor.jsx`, `useLatexSync.js` | — | `FormulaEditor.test: textarea (7), MathLive (2), error handling` | ✅ |
| FR2-03 | Overlay pointer/keyboard | `RegionOverlay.jsx`, `App.jsx` | — | `RegionOverlay.test: 20 tests (positioning, drag, resize, keyboard, a11y)` | ✅ |

## FR3 — Submit LaTeX

| ID | Yêu cầu | Code | Backend test | Frontend test | Trạng thái |
|---|---|---|---|---|---|
| FR3-01 | `POST .../submit` ghi `latex_final` | `api/formulas.py` | `test_formula_submit.py` (ghi OK, 409 chưa OCR, owner) | `FormulaEditor.test: submit button (4 tests)` | ✅ |
| FR3-02 | `latex_raw` không đổi | `api/formulas.py` | `test_formula_submit.py` (3 test bảo vệ) | — | ✅ |
| FR3-03 | Reload giữ `latex_final` | `GET .../formulas` | `test_submit_is_logged_and_persists_across_reload` | `FormulaEditor.test: OCR raw display (2 tests)` | ✅ |

## FR4 — Lịch sử tải lên

| ID | Yêu cầu | Code | Backend test | Frontend test | Trạng thái |
|---|---|---|---|---|---|
| FR4-01 | Liệt kê/mở/xóa | `api/documents.py` | `test_list_*`, `test_delete_*` | `DocumentFlow.test: history (3 tests)` | ✅ |
| FR4-02 | Tải PDF gốc | `GET .../source` | `test_download_source_pdf` | — | ✅ |
| FR4-03 | Xuất `.tex` | `GET .../export` | `test_export_*` | — | ✅ |
| FR4-04 | Không xóa khi đang xử lý | `api/documents.py` | `test_delete_is_blocked_while_processing` | — | ✅ |

## NFR — Phi chức năng

| ID | Yêu cầu | Code | Test | Trạng thái |
|---|---|---|---|---|
| NFR-01 | DB schema | models + Compose | Gián tiếp qua API test | ✅ |
| NFR-02 | Migration có phiên bản | `alembic/versions/*` | Drill thủ công S1-02 | ⬜ |
| NFR-03 | GPU/CPU config | `services/formula_regions.py` | Kiểm CPU S1-06 | ⬜ |
| NFR-04 | Đánh giá accuracy | `scripts/evaluate_metrics.py` | Script chạy được; chưa có dữ liệu submitted | 🟡 |
| NFR-05 | Không lộ secret | `core/security.py`, `action_log.py` | `test_passwords_and_tokens_are_never_logged` | ✅ |
| NFR-06 | Queue reliability | `core/queue.py`, worker services | `test_ocr_queue*.py`, `tests/worker/` | ✅ |
| NFR-07 | Upload limits | `core/limits.py`, `upload_validation.py` | `test_upload_validation.py`, `test_sanitize_filename.py` | ✅ |

## Tổng kết

| Metric | Số lượng |
|---|---|
| Tổng yêu cầu FR | 17 |
| Có test tự động | 17/17 (100%) |
| Tổng yêu cầu NFR | 7 |
| Có test tự động | 5/7 (71%) |
| Backend test files | 18 files, 182+ tests |
| Frontend test files | 3 files, 60 tests |
| Khoảng trống còn lại | NFR-02 (migration drill), NFR-03 (GPU check), NFR-04 (cần submitted data) |
