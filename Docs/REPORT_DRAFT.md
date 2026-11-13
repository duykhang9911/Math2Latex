# Báo cáo đồ án tốt nghiệp — Math2Latex (Bản nháp S6-01)

> **Lưu ý:** Đây là bản nháp nội dung các chương. Cần đối chiếu với mẫu báo cáo của khoa (D-05) khi có.

---

## Chương 1: Tổng quan

### 1.1 Đặt vấn đề

Tài liệu toán học dưới dạng PDF được sử dụng rộng rãi trong giáo dục và nghiên cứu. Tuy nhiên, các công thức toán trong PDF không thể sao chép hay chỉnh sửa trực tiếp. Việc chuyển đổi thủ công sang định dạng LaTeX tốn nhiều thời gian và dễ sai sót.

Gần đây, các mô hình nhận dạng ký tự quang học (OCR) chuyên biệt cho công thức toán đã đạt được tiến bộ đáng kể. Tuy nhiên, kết quả OCR thường không hoàn hảo — đặc biệt với các công thức phức tạp — nên vẫn cần bước review và chỉnh sửa của con người.

### 1.2 Mục tiêu

Xây dựng ứng dụng web **Math2Latex** cho phép:
1. Upload file PDF chứa công thức toán
2. Tự động phát hiện vùng công thức (bounding box)
3. Nhận dạng từng vùng thành LaTeX thô (`latex_raw`)
4. Cho phép người dùng review, chỉnh sửa trực quan qua giao diện MathLive
5. Lưu kết quả (`latex_final`) và xuất file `.tex`

### 1.3 Phạm vi

**Trong phạm vi:** Upload PDF, detect bbox, OCR LaTeX, sửa vùng bằng pointer/keyboard, đồng bộ LaTeX ↔ MathLive, Submit lưu DB, lịch sử tải lên, export `.tex`, bảo mật cơ bản (Argon2, JWT, owner scoping).

**Ngoài phạm vi:** Role admin, reset mật khẩu, xác minh email, OCR text toàn trang, collaborative editing, SLA production.

### 1.4 Cấu trúc báo cáo

Chương 2: Cơ sở lý thuyết. Chương 3: Phân tích yêu cầu. Chương 4: Thiết kế. Chương 5: Triển khai. Chương 6: Kiểm thử và đánh giá. Chương 7: Kết luận.

---

## Chương 2: Cơ sở lý thuyết

### 2.1 LaTeX
- Hệ thống soạn thảo toán học phổ biến nhất
- Cú pháp: `\frac{a}{b}`, `\sqrt{x}`, `\sum_{i=1}^{n}`

### 2.2 Nhận dạng công thức toán (Math OCR)
- **Pix2Text MFD (Math Formula Detection):** Mô hình phát hiện vùng công thức trong ảnh, sử dụng YOLOv8 backbone, xuất bbox
- **pix2tex (LaTeX OCR):** Mô hình seq2seq (ViT encoder + Transformer decoder) chuyển ảnh crop thành chuỗi LaTeX
- **ONNX Runtime:** Framework inference cross-platform, hỗ trợ CPU/GPU

### 2.3 Công nghệ web
- **React 19 + Vite 8:** Framework SPA hiện đại
- **MathLive:** Web component hiển thị và chỉnh sửa toán học trực quan
- **FastAPI:** Framework Python async cho REST API
- **PostgreSQL:** RDBMS lưu trữ chính
- **Redis + RQ (Redis Queue):** Hàng đợi job nền

### 2.4 Docker Compose
- Container hóa ứng dụng đa dịch vụ
- Tái lập môi trường nhất quán giữa các máy

---

## Chương 3: Phân tích yêu cầu

### 3.1 Tác nhân (Actors)
- **Người dùng (User):** Upload PDF, review công thức, chỉnh sửa LaTeX, xuất kết quả

### 3.2 Yêu cầu chức năng

| ID | Yêu cầu | Mô tả |
|---|---|---|
| FR0 | Xác thực | Đăng ký, đăng nhập, đăng xuất với Argon2 hash + JWT cookie |
| FR1 | Upload → Detect → OCR | Upload PDF, render trang, detect bbox, crop, OCR sinh `latex_raw` |
| FR2 | Sửa LaTeX ↔ MathLive | Sửa vùng bằng pointer/keyboard; textarea LaTeX đồng bộ MathLive |
| FR3 | Submit | Ghi `latex_final`, giữ nguyên `latex_raw` |
| FR4 | Lịch sử | Liệt kê/mở/xóa document, tải PDF gốc, xuất `.tex` |

### 3.3 Yêu cầu phi chức năng

| ID | Yêu cầu |
|---|---|
| NFR-01 | Dữ liệu lưu trong PostgreSQL |
| NFR-02 | Migration có phiên bản (Alembic) |
| NFR-03 | Hỗ trợ CPU/GPU qua cấu hình |
| NFR-04 | Đánh giá accuracy có dữ liệu thật |
| NFR-05 | Không lộ password/token trong log |
| NFR-06 | Queue tin cậy (Redis + RQ) |
| NFR-07 | Giới hạn upload (size, type, filename) |

### 3.4 Use Case Diagram

*(Xem sơ đồ trong ARCHITECTURE.md hoặc S6-02)*

---

## Chương 4: Thiết kế

### 4.1 Kiến trúc tổng quan

Hệ thống gồm 5 service Docker Compose:
1. **frontend** (React + Vite) — giao diện người dùng
2. **backend** (FastAPI) — REST API, validation, enqueue job
3. **worker** (RQ) — xử lý nền (detect, OCR)
4. **db** (PostgreSQL) — nguồn sự thật
5. **redis** — điều phối job queue

### 4.2 Cơ sở dữ liệu (ER)

**Bảng chính:**
- `users` (id, username, password_hash, created_at)
- `documents` (id, filename, status, uploaded_by FK, page_count, file_size_bytes)
- `formula_entries` (id, document_id FK, page_number, status, x_min/y_min/x_max/y_max, latex_raw, latex_final, confidence)
- `action_logs` (id, document_id, action, detail, created_at)

**Status transitions:**
```
uploaded → processing_pages → detecting_formulas → formula_proposals_ready
                                                        ↓
                              ocr_complete ← ocr_processing
                              ocr_completed_with_errors ←┘
                              processing_failed (bất kỳ bước nào lỗi)
```

### 4.3 API Design

21 endpoint REST:
- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `POST /api/documents/upload`, `GET /api/documents`, `GET /api/documents/{id}`
- `GET /api/documents/{id}/pages`, `GET /api/documents/{id}/pages/{n}/image`
- `GET /api/documents/{id}/formulas`, `POST /api/documents/{id}/formulas`
- `PATCH /api/documents/{id}/formulas/{fid}`, `DELETE /api/documents/{id}/formulas/{fid}`
- `GET /api/documents/{id}/formulas/{fid}/image`
- `POST /api/documents/{id}/formulas/recognize`, `POST /api/documents/{id}/formulas/retry`
- `POST /api/documents/{id}/formulas/{fid}/submit`
- `GET /api/documents/{id}/source`, `GET /api/documents/{id}/export`
- `DELETE /api/documents/{id}`

### 4.4 Frontend Components

Sau refactor S4-01:
- `App.jsx` — layout, state, routing logic
- `api/client.js` — API constants, fetch wrapper, helpers
- `components/PDFUploader.jsx` — form upload
- `components/HistoryPanel.jsx` — danh sách lịch sử
- `components/RegionOverlay.jsx` — bbox overlay trên ảnh trang
- `components/FormulaEditor.jsx` — crop, LaTeX textarea, MathLive, Submit
- `hooks/useLatexSync.js` — sync MathLive ↔ controlled value

---

## Chương 5: Triển khai

### 5.1 Cấu trúc mã nguồn

```
Math2Latex/
├── backend/
│   ├── api/           # Route handlers (auth, documents, formulas, deps)
│   ├── core/          # Security, queue, limits, storage
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic (pdf_pages, formula_regions, formula_ocr, ...)
│   ├── alembic/       # Database migrations (5 versions)
│   ├── scripts/       # Evaluation scripts
│   └── tests/         # 18 test files, 182+ tests
├── frontend/
│   ├── src/
│   │   ├── api/       # API client
│   │   ├── components/# React components
│   │   ├── hooks/     # Custom hooks
│   │   ├── App.jsx    # Main component
│   │   └── App.css    # Styles (+ Tailwind)
│   └── tests/         # 3 test suites, 60 tests
├── docker-compose.yml
├── Docs/              # SRS, ARCHITECTURE, SETUP, PLAYBOOK, ...
└── .env               # Environment config
```

### 5.2 Quy trình xử lý PDF

1. User upload → `POST /upload` validate (type, size) → lưu file → enqueue job `process_pdf`
2. Worker nhận job → PyMuPDF render trang → lưu ảnh → Pix2Text MFD detect bbox → tạo `formula_entries` status `proposed`
3. User xác nhận vùng → `POST /recognize` → enqueue job `ocr_formulas`
4. Worker nhận job → pix2tex OCR từng crop → ghi `latex_raw` → status `ocr_complete`

### 5.3 Bảo mật

- Mật khẩu hash Argon2id (không MD5/SHA)
- JWT token trong HttpOnly cookie (không localStorage)
- Rate limit 5 lần/15 phút per IP+username (Redis counter)
- Origin check cho mọi request ghi
- Owner scoping: chỉ thấy document của mình
- Upload validation: max 100MB, chỉ PDF, filename sanitize

### 5.4 Error Handling (S3-07)

Frontend hiển thị thông báo cụ thể cho từng mã lỗi:
- 400: "Yêu cầu không hợp lệ"
- 401: Auto-logout + "Phiên đăng nhập đã hết hạn"
- 413: "File quá lớn"
- 422: "Dữ liệu không hợp lệ"
- 429: "Bạn đã gửi quá nhiều yêu cầu"

---

## Chương 6: Kiểm thử và đánh giá

### 6.1 Kiểm thử tự động

| Loại | Số test | Công cụ | Ghi chú |
|---|---|---|---|
| Backend API | 100+ | pytest, httpx | SQLite cho unit, PostgreSQL cho concurrency |
| Backend unit | 40+ | pytest | Schemas, sanitize, queue |
| Backend worker | 10+ | pytest | Fake model, job error handling |
| Frontend component | 60 | Vitest, jsdom | FormulaEditor, RegionOverlay, DocumentFlow |
| **Tổng** | **242+** | | |

### 6.2 Ma trận truy vết

17/17 yêu cầu chức năng (FR) có test tự động. 5/7 yêu cầu phi chức năng (NFR) có test. Chi tiết xem [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md).

### 6.3 Đánh giá chất lượng mô hình

**Detector (Pix2Text MFD):**
- Phát hiện 103–1709 vùng/document tùy mật độ công thức
- Chạy trên CPU ~2s/trang (17 trang test)
- Precision/Recall chính xác cần bbox ground truth thủ công (chưa có)

**OCR (pix2tex):**
- Cold start ~8s, warm <1s/công thức
- RAM ~1.5GB
- Exact match / edit distance cần dữ liệu submitted (xem `evaluate_metrics.py`)

**Hạn chế:** Chưa có ground truth đã review thủ công nên chưa tính được precision/recall/exact-match chính thức.

### 6.4 Latency (S5-04)

| Metric | Giá trị |
|---|---|
| PDF render | ~0.5s/trang |
| Detect (MFD, cold) | ~8s |
| Detect (MFD, warm) | ~2s/trang |
| OCR (cold) | ~8s |
| OCR (warm) | <1s/công thức |
| RAM worker | ~1.5GB |

---

## Chương 7: Kết luận

### 7.1 Kết quả đạt được

- Hệ thống Math2Latex hoạt động end-to-end trên Docker Compose
- 4 chức năng chính (FR0–FR4) đầy đủ: upload, detect, OCR, review/edit, submit, export
- Giao diện trực quan với MathLive cho chỉnh sửa công thức
- 242+ test tự động, 100% FR có test
- Tài liệu kỹ thuật đầy đủ

### 7.2 Hạn chế

1. Chỉ chạy CPU — chưa tối ưu GPU
2. Dữ liệu đánh giá ít (3–4 file PDF)
3. OCR sai với công thức phức tạp (ma trận lớn, ký hiệu đặc biệt)
4. Chưa hỗ trợ inline math detection riêng
5. MathLive không render được một số ký hiệu LaTeX nâng cao

### 7.3 Hướng phát triển

1. GPU support qua NVIDIA Docker
2. Batch processing nhiều PDF
3. Fine-tune pix2tex trên dữ liệu Việt Nam
4. Tích hợp LLM (GPT/Gemini) cho post-correction
5. Collaborative editing (nhiều người cùng review)
6. Export sang nhiều định dạng (Markdown, Word)
