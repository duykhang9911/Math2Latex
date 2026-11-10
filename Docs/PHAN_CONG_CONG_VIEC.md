# Kế hoạch đồ án tốt nghiệp Math2Latex (12 tuần, 2 thành viên)

Tài liệu này là nguồn chuẩn cho phạm vi, phân công, lịch và điều kiện hoàn thành của đồ án. Yêu cầu chi tiết nằm ở [SRS](SRS.md); kiến trúc ở [ARCHITECTURE](ARCHITECTURE.md); quy trình làm feature ở [DEVELOPMENT_PLAYBOOK](DEVELOPMENT_PLAYBOOK.md).

## 1. Thông tin chung

| Mục | Nội dung |
|---|---|
| Đề tài | Math2Latex — chuyển công thức trong PDF thành LaTeX có thể chỉnh sửa |
| Thời lượng | 12 tuần, chia 6 sprint × 2 tuần |
| Điểm dừng | Mục 8 — Definition of Done của đồ án |
| Thành viên | Đoàn Trương Duy Khang, Ngô Hồ Tuấn Toàn (xem [TEAM](TEAM.md)) |
| Kế hoạch đã duyệt | `Ke-hoach-du-an-Math2Latex-da-cap-nhat.docx` (FR1–FR3, công nghệ, lộ trình 12 tuần, rủi ro). Tài liệu này là bản kỹ thuật chi tiết của kế hoạch đó; mục 2.4 đối chiếu từng hạng mục. Nếu hai bên khác nhau thì kế hoạch đã duyệt thắng, trừ khi nhóm đổi qua mục 9 |
| Chưa có thông tin | MSSV, lớp/môn, giảng viên hướng dẫn, ngày nộp/bảo vệ, mẫu báo cáo của khoa. Không tự điền; nhập vào [TEAM](TEAM.md) khi có |

Mọi con số effort là **người-ngày (PD)** ước lượng để nhóm điều chỉnh, không phải cam kết.

## 2. Phạm vi đồ án

### 2.1 Trong phạm vi

| ID | Chức năng | Trạng thái mã nguồn | Việc còn lại để đạt điểm dừng |
|---|---|---|---|
| FR0 | Đăng ký/đăng nhập/đăng xuất, Argon2 + JWT cookie, owner scoping | Đã có + test API | Hardening (S3), test hết hạn/giả mạo token |
| FR1 | Upload PDF → render → detect bbox → crop → OCR `latex_raw` qua queue | Đã có, đã chạy bằng ONNX CPU | Idempotency, phục hồi job treo, quyết định GPU/CPU, giới hạn upload (S2, S3) |
| FR2 | Sửa vùng bằng pointer/keyboard; LaTeX ↔ MathLive hai chiều | Đã có | Kiểm thử keyboard/touch/font, test tự động (S4) |
| FR3 | Submit ghi `latex_final`, giữ nguyên `latex_raw` | Đã có | Test hành vi resubmit, lỗi API (S4) |
| FR4 | Lịch sử tải lên: liệt kê/mở/xóa, tải PDF gốc, xuất `.tex` từ `latex_final` | Đã có + test API | Test UI, retention/cleanup (S3, S4) |
| NFR | Độ tin cậy queue, bảo mật upload/auth, tái lập môi trường, đánh giá accuracy có dữ liệu thật | Một phần | Toàn bộ S2–S5 |

### 2.2 Ngoài phạm vi (giữ nguyên theo SRS §5)

Role Admin, reset mật khẩu, xác minh email, pipeline ảnh đơn lẻ, OCR text toàn trang, collaborative editing, SLA production. Muốn đưa mục nào vào phải quyết định ở **D-01** (mục 9) trước hết Sprint 2; sau đó mới đổi SRS và lịch này.

### 2.3 Công nghệ và lý do giữ lại

Chỉ giữ công nghệ nằm trong kế hoạch đã duyệt hoặc đã có trong `requirements.txt`/`package.json`/Compose và đang được code dùng. Không thêm thư viện khác khi chưa có quyết định ở mục 9.

| Công nghệ | Vai trò duy nhất trong đồ án |
|---|---|
| React + Vite | Giao diện review PDF/công thức |
| Tailwind CSS | Style giao diện — **có trong kế hoạch đã duyệt, chưa cài**; thay `App.css` ở S4-09 |
| MathLive | Editor công thức, đồng bộ với textarea LaTeX |
| FastAPI | API, validation HTTP, enqueue job |
| SQLAlchemy + Alembic | ORM và migration có phiên bản |
| PostgreSQL | Nguồn sự thật cho user/document/formula/log |
| Redis + RQ | Điều phối job nền; không lưu kết quả chính |
| PyMuPDF + Pillow | Render trang PDF, cắt crop theo bbox |
| Pix2Text MFD | Đề xuất vùng công thức |
| pix2tex | Nhận dạng crop → `latex_raw` |
| Argon2 (argon2-cffi) + PyJWT | Băm mật khẩu, access token trong cookie HttpOnly |
| Docker Compose | Chạy lại toàn bộ hệ thống trên máy khác |
| pytest, ESLint | Test backend, lint frontend |

### 2.4 Đối chiếu với kế hoạch đã duyệt

Các ô "Trạng thái" trong file docx đã cũ so với mã nguồn hiện tại. Bảng dưới là hiện trạng đã kiểm tra trong code ngày 2026-11-10.

| Hạng mục đã duyệt | Hiện trạng trong code | Việc còn lại |
|---|---|---|
| FR1 đọc PDF, chỉ lấy công thức | Có: PyMuPDF render, Pix2Text MFD detect, crop | Đánh giá chất lượng (S5) |
| FR2 sửa LaTeX ↔ MathLive hai chiều | Có, nằm trong `App.jsx` | Tách đơn vị theo đúng tên trong docx, test (S4-01…S4-04) |
| FR3 Submit lưu DB | Có: `POST /formulas/{id}/submit` ghi `latex_final`, ghi log `submit` | Test (S4-04) |
| Bảng `documents`: `uploaded_by` FK | Đã có FK `ON DELETE SET NULL` (migration `a6b0f1c2d3e4`) | — |
| `documents.status`, `formula_entries.status` là enum | Vẫn là `String`; giá trị thực tế khác docx (xem dưới) | S3-09 |
| `users`, `logs` | Đã dùng: đăng ký/đăng nhập; log upload/submit/lịch sử/queue | — |
| Upload chỉ PDF, giới hạn dung lượng | Có: chỉ `.pdf`, tối đa 100 MB, stream | Số trang, pixel, timeout, validate nội dung (S3-01, S3-02) |
| `POST /api/documents/{id}/process` trả công thức đồng bộ | Không có; thay bằng xử lý nền: upload tự enqueue, `GET …/formulas`, `POST …/formulas/recognize` (202) | Quyết định D-09 |
| `services/api.js`, `PDFUploader`, `Preview`, `MathLiveEditor`, `useLatexSync` | Chưa tách; logic trong `App.jsx` | S4-01 |
| Tailwind CSS | Chưa cài | S4-09 |
| Xử lý bất đồng bộ (mục 6, tuỳ chọn) | Đã làm bằng Redis + RQ (docx nêu Celery/Redis hoặc BackgroundTasks) | Độ tin cậy S2 |
| ONNX Runtime (mục 6, tuỳ chọn) | Pix2Text MFD chạy ONNX; GPU/CPU chưa chốt | S2-05 |
| BLEU / edit-distance (mục 7, 12) | Chưa có | S5-03 |
| Texo, dots.ocr/GLM-OCR, Mathpix/VLM, WebSocket (mục 6) | Chưa có, ngoài lịch | Quyết định D-10 |

Giá trị trạng thái thực tế trong code (docx ghi `uploaded/processing/done/failed` và `pending/edited/submitted`):

- Document: `processing_pages` → `detecting_formulas` → `formula_proposals_ready` → `ocr_processing` → `ocr_complete` / `ocr_completed_with_errors`; lỗi render là `processing_failed`.
- Formula: `proposed` → `ocr_queued` → `ocr_complete` / `ocr_failed` → `submitted`.

## 3. Phân công

| Vai trò | Thành viên | Chịu trách nhiệm chính (R/A) | Review (C) |
|---|---|---|---|
| Backend/Platform | Đoàn Trương Duy Khang | API, models/migration, Redis/RQ, worker, PDF/MFD/OCR, Docker/GPU runtime, auth backend, test backend, sơ đồ backend/runtime | Frontend, contract UI, báo cáo phần kỹ thuật |
| Frontend/QA/Docs | Ngô Hồ Tuấn Toàn | React/MathLive, accessibility, test frontend/browser, bộ PDF và đánh giá accuracy, báo cáo/slides/demo | API, bbox, hành vi persistence, queue |

Quy tắc:

- Mỗi task có đúng **một owner**; người còn lại là reviewer. Không merge việc của mình khi chưa có review (nhánh/PR theo [GIT_WORKFLOW](GIT_WORKFLOW.md)).
- Chốt API/schema/status trước khi hai bên làm song song; đổi contract phải cập nhật SRS/ARCHITECTURE cùng PR.
- Khang không tự kết luận độ chính xác OCR; Toàn không che lỗi backend bằng state UI.
- Cả hai cùng ký xác nhận mỗi gate và bản demo cuối.

## 4. Lộ trình 12 tuần

```text
Tuần:        1   2 | 3   4 | 5   6 | 7   8 | 9  10 | 11  12
Sprint:       S1    |  S2   |  S3   |  S4   |  S5   |  S6
Trọng tâm:  Nền    | Queue | Bảo   | UI +  | Đánh  | Báo cáo
            tảng   | + GPU | mật   | test  | giá   | + demo
Gate:          G1      G2      G3      G4      G5      G6
Thu thập PDF đánh giá: ======= (song song từ S1) ========
Feature freeze:                                 ^ cuối S4 (tuần 8)
```

Từ sau G4 chỉ sửa lỗi có bằng chứng; không thêm chức năng.

### Sprint 1 (tuần 1–2) — Nền tảng và chốt contract

| ID | Task | Owner | Reviewer | PD | Sản phẩm/nghiệm thu |
|---|---|---|---|---|---|
| S1-01 | Commit sạch các thay đổi đang dở theo nhóm nhỏ; chạy `docker compose config -q`, `up -d --build`, `alembic upgrade head`; health 5 service | Khang | Toàn | 1 | `git status` sạch; `/health` 200; `rq info` thấy worker |
| S1-02 | Test migration từ DB rỗng và từ DB có dữ liệu cũ | Khang | Toàn | 1 | Ghi lệnh + kết quả vào [DATABASE](DATABASE.md) |
| S1-03 | Gán ID cho yêu cầu trong SRS, dựng khung ma trận truy vết (mục 7) | Toàn | Khang | 1 | SRS có ID; ma trận có cột test |
| S1-04 | Xin/thu thập PDF toán được phép dùng; ghi nguồn và quyền sử dụng | Toàn | Khang | 2 | Danh sách nguồn có xác nhận quyền; không commit PDF |
| S1-05 | Chốt contract từ Swagger: bbox pixel, page từ 1, state transition document/formula | Khang + Toàn | nhau | 1 | ARCHITECTURE/SRS khớp OpenAPI |
| S1-06 | Xác minh runtime trong worker: `torch.cuda.is_available()`, ONNX providers, inference thật | Khang | Toàn | 1 | Log provider; không dùng `nvidia-smi` làm bằng chứng |
| S1-07 | Smoke test upload mới bằng PDF được phép | Toàn | Khang | 0.5 | Upload → bbox → OCR → Submit chạy được |

**Gate G1:** stack chạy từ clone sạch; contract khóa; biết GPU hay CPU; có ít nhất 1 PDF hợp lệ.

**Tiến độ Sprint 1 (cập nhật 2026-11-10):**

| Task | Trạng thái |
|---|---|
| S1-01, S1-02, S1-03, S1-04, S1-06, S1-07 | Xong |
| S1-05 | Xong phần tài liệu: bảng API trong ARCHITECTURE khớp OpenAPI; chờ Toàn review và quyết định D-09 để khóa |
| S1-04 (ghi chú) | Dữ liệu là các PDF đã upload vào ứng dụng, chủ dự án xác nhận được dùng 2026-11-10 ([DATASET](DATASET.md)); cần ghi `document_id` bản chuẩn cho từng file ở S5-01 |
| S1-07 | Xong 2026-11-10 với `2022-MathMethods1.pdf` (17 trang, CPU; file này không thuộc dữ liệu đánh giá): sau khi ghim `rapidocr>=3.9,<3.10` (bản 3.10.0 làm `pix2text` không import được), detect ra 130 vùng trong ~35 s, OCR 130 vùng trong ~46 s, Submit giữ nguyên `latex_raw`, export `.tex` đúng. Chỉ là smoke test chức năng, chưa phải đo độ chính xác. Dữ liệu tạm đã xóa, DB về 1 user/15 document/1669 công thức |

### Sprint 2 (tuần 3–4) — Độ tin cậy hàng đợi và GPU/CPU

| ID | Task | Owner | Reviewer | PD | Sản phẩm/nghiệm thu |
|---|---|---|---|---|---|
| S2-01 | Chống enqueue kép recognize/retry: code đã có `with_for_update` và kiểm tra status; còn thiếu test đồng thời và kiểm tra idempotency phía worker | Khang | Toàn | 2 | Test: 2 request đồng thời chỉ tạo 1 job hợp lệ |
| S2-02 | Redis không nhận job: code đã hoàn tác status và trả 503; còn thiếu test với Redis giả lỗi, và nhánh upload/retry cùng cách xử lý | Khang | Toàn | 1.5 | Test API với Redis giả lỗi |
| S2-03 | Timeout/retry/failure visibility; phục hồi formula `ocr_queued` treo khi worker chết | Khang | Toàn | 2 | Test worker restart; không còn state mơ hồ |
| S2-04 | Kiểm Redis AOF/volume khi restart Redis/backend/worker | Khang | Toàn | 1 | Biên bản drill ghi trong SETUP |
| S2-05 | Chọn cấu hình suy luận: ONNX CUDA, `MATH_DETECTOR_BACKEND=pytorch` trên CUDA, hoặc CPU fallback có giới hạn rõ | Khang | Toàn | 1.5 | Bảng latency/VRAM/RAM thật; cấu hình chốt trong Compose |
| S2-06 | Ma trận test lỗi (Redis down, OCR exception, PDF hỏng) và UI states queued/failed/retry | Toàn | Khang | 2 | Test matrix; UI hiển thị đúng từng trạng thái |
| S2-07 | Tạo `backend/tests/worker/` | Khang | Toàn | 1 | Chạy được bằng lệnh trong tests/README |

**Gate G2:** queue an toàn khi lặp/restart; GPU/CPU chốt bằng bằng chứng; **D-01 đã được quyết định**.

**Tiến độ Sprint 2 (cập nhật 2026-11-10):**

| Task | Trạng thái |
|---|---|
| S2-01 | Xong: `tests/api/test_ocr_queue.py`, `tests/api/test_ocr_queue_concurrency.py` (PostgreSQL; bỏ `with_for_update` thì test chờ khóa fail). Worker bỏ qua công thức/document đã được job khác xử lý; có test |
| S2-02 | Xong cho upload/recognize/retry: Redis lỗi → 503, state hoàn tác, gọi lại được (test + thử thật). Đã sửa: lỗi ghi log sau khi job đã vào queue không còn hoàn tác state (`_log_action_after_enqueue`, có test đã chứng minh fail trên code cũ) |
| S2-03 | Xong: mọi job kèm RQ `on_failure`; worker chết giữa OCR → công thức `ocr_queued` về `ocr_failed`, document `ocr_completed_with_errors`, retry được (drill thật). Còn lại: document kẹt khi mất dữ liệu Redis; UI chưa báo job quá hạn khi không có worker |
| S2-04 | Xong: Redis AOF giữ job khi restart Redis (drill thật); upload khi Redis down → 503. Ghi trong [ARCHITECTURE](ARCHITECTURE.md) |
| S2-05 | Xong với **CPU**: đã đo latency/RAM thật (ARCHITECTURE). Cấu hình CUDA chưa đo vì chưa có GPU trong Docker; không chọn ngầm |
| S2-06 | Phần backend xong; ma trận lỗi ở [DEVELOPMENT_PLAYBOOK](DEVELOPMENT_PLAYBOOK.md). Phần UI mới đọc code, **chưa kiểm bằng trình duyệt** (Toàn) |
| S2-07 | Xong: `tests/worker/` (15 test); toàn bộ suite 51 pass + 2 PostgreSQL (53 pass khi có `TEST_PG_URL`) |

**Gate G2:** queue an toàn khi lặp/restart: đạt (bằng test và drill). GPU/CPU chốt bằng bằng chứng: đạt với CPU, GPU chưa đo. **D-01 chưa được quyết định**: cần chủ dự án trả lời. Còn thiếu để đóng hẳn: Toàn kiểm UI queued/failed/retry bằng trình duyệt.
### Sprint 3 (tuần 5–6) — Bảo mật, giới hạn và vòng đời dữ liệu

| ID | Task | Owner | Reviewer | PD | Sản phẩm/nghiệm thu |
|---|---|---|---|---|---|
| S3-01 | Giới hạn upload: bytes (đã có 100 MB), số trang, pixel, timeout xử lý | Khang | Toàn | 1.5 | Lỗi thân thiện, có test |
| S3-02 | Validate nội dung PDF: mã hóa, hỏng, tên file/path abuse | Khang | Toàn | 1.5 | Test fixture synthetic |
| S3-03 | Retention/cleanup: source, pages, crops, job lỗi, file mồ côi (không được xóa các document dữ liệu trong [DATASET](DATASET.md), kể cả 14 document chưa có owner) | Khang | Toàn | 2 | Chính sách ghi trong DATABASE; test không xóa dữ liệu hợp lệ |
| S3-04 | Hardening auth: rate limit đăng nhập (**D-03**), policy đổi `AUTH_SECRET`, cookie Secure/CSRF dưới HTTPS, hết phiên | Khang | Toàn | 2 | Test + ghi trong ARCHITECTURE |
| S3-05 | Quy trình chuyển owner cho document cũ `uploaded_by IS NULL` (**D-07**) | Khang | Toàn | 0.5 | Quy tắc ghi trong DATABASE |
| S3-06 | Dọn code backend: tách `api/documents.py` (562 dòng) thành router mỏng + service; không đổi contract | Khang | Toàn | 2 | Test hiện có vẫn pass; diff chỉ di chuyển/tách |
| S3-07 | UX lỗi giới hạn upload, hết phiên, đăng nhập/đăng ký | Toàn | Khang | 1.5 | Browser check |
| S3-08 | Chọn test runner frontend (**D-02**) và dựng khung | Toàn | Khang | 1 | `npm test` chạy được, ghi vào frontend/tests/README |
| S3-09 | Ràng buộc `status` theo kế hoạch đã duyệt (enum hoặc CHECK constraint) cho `documents` và `formula_entries`; migration mới, backfill giá trị hiện có | Khang | Toàn | 1.5 | Migration chạy trên DB rỗng và DB có dữ liệu; giá trị lạ bị DB từ chối |

**Gate G3:** upload độc hại/hỏng bị từ chối có thông báo; cleanup an toàn; backend test suite pass.

**Tiến độ Sprint 3 — phần của Khang (cập nhật 2026-11-10):**

| Task | Trạng thái |
|---|---|
| S3-01 | Xong: giới hạn dung lượng 100 MB, 200 trang, 25 triệu pixel/trang, timeout job PDF 1800 s / OCR 3600 s (đổi bằng biến môi trường; **giá trị do nhóm chọn, cần xác nhận**). Bảng ở [ARCHITECTURE](ARCHITECTURE.md) |
| S3-02 | Xong: phải là PDF thật (kể cả ảnh đổi đuôi `.pdf` — lỗ hổng phát hiện nhờ test), không cần mật khẩu, tên file sạch, upload bị từ chối không để lại file/dòng database (trước đây vượt dung lượng để lại thư mục rồi). Đã kiểm 11 PDF thật trong `uploads/`: không bị từ chối nhầm |
| S3-03 | Xong: `python -m app.services.retention` (dry-run mặc định); chính sách trong [DATABASE](DATABASE.md). Chạy dry-run trên dữ liệu thật: 0 thư mục mồ côi, các document dữ liệu không bị đụng tới |
| S3-04 | Xong: giới hạn đăng nhập sai (Redis, 5 lần/15 phút cho mỗi IP+username, 429), kiểm tra Origin cho request ghi, `CORS_ORIGINS` cấu hình được, test token hết hạn/giả mạo/đổi secret, cờ cookie, không lộ bí mật trong log. Cách rate limit tự viết trên Redis (không thêm thư viện) theo mặc định của D-03. Còn lại: UX báo 429 và hết phiên ở UI (S3-07, Toàn) |
| S3-05 | Xong phần tài liệu: quy trình SQL chuyển owner trong [DATABASE](DATABASE.md); chưa thực hiện vì D-07 chưa quyết định |
| S3-06 | Xong: `api/documents.py` 662 → 253 dòng; tách `api/formulas.py`, `api/deps.py` và các service (`ocr_queue`, `document_queries`, `latex_export`, `action_log`, `core/storage`). Contract không đổi (21 route khớp OpenAPI), 141 test pass, chạy lại end-to-end thật |
| S3-09 | Xong: CHECK constraint thay vì enum (khác kế hoạch đã duyệt vì dễ mở rộng hơn), migration `c8d2e3f4a5b6` đã chạy thử trên bản khôi phục dữ liệu thật và đã áp dụng vào DB dev |
| S3-07, S3-08 | Việc của Toàn, chưa làm |

**Gate G3:** upload hỏng/mã hóa/quá giới hạn bị từ chối có thông báo: đạt; cleanup an toàn: đạt; backend test suite pass: đạt (141 test, gồm PostgreSQL và Redis thật). Còn chờ S3-07, S3-08 của Toàn.
### Sprint 4 (tuần 7–8) — Hoàn thiện giao diện và kiểm thử → **Feature freeze**

| ID | Task | Owner | Reviewer | PD | Sản phẩm/nghiệm thu |
|---|---|---|---|---|---|
| S4-01 | Dọn code frontend: tách `App.jsx` (688 dòng) thành `services/api.js`, `PDFUploader`, `Preview`, `MathLiveEditor`, `hooks/useLatexSync` (tên theo kế hoạch đã duyệt; **một state LaTeX duy nhất** làm nguồn chân lý) | Toàn | Khang | 2.5 | Hành vi không đổi; build + lint pass |
| S4-02 | Test LaTeX ↔ MathLive: phân số, căn, ma trận, Greek, cú pháp lỗi | Toàn | Khang | 1.5 | Test tự động |
| S4-03 | Test overlay: pointer, Tab/arrows/Alt+arrows/Shift 10 px, bounds | Toàn | Khang | 2 | Test + checklist keyboard-only |
| S4-04 | Test luồng document: upload, polling, OCR thành công/lỗi/retry, Submit, reload raw/final | Toàn | Khang | 2 | Test + bằng chứng `latex_raw` không đổi |
| S4-05 | UI lịch sử: mở/xóa/tải PDF/export `.tex`, trạng thái rỗng/lỗi | Toàn | Khang | 1.5 | Browser check |
| S4-06 | Font MathLive local sau build/restart (WOFF2 200, không lỗi console); kiểm tra mobile/touch | Toàn | Khang | 1 | Biên bản desktop + mobile |
| S4-07 | Bổ sung test backend cho schemas/bounds/state/API còn thiếu | Khang | Toàn | 2 | Báo cáo test chạy được bằng lệnh tài liệu hóa |
| S4-08 | Review chéo contract API ↔ UI; sửa lệch | Khang + Toàn | nhau | 1 | Không còn khác biệt SRS/code |
| S4-09 | Cài Tailwind CSS và chuyển style từ `App.css` (719 dòng) sang Tailwind; chỉ làm sau S4-01 | Toàn | Khang | 3 | Giao diện không đổi hành vi; keyboard focus/contrast còn đúng; `npm run build` + `lint` pass |
| S4-10 | Bắt lỗi MathLive không parse được LaTeX: hiện cảnh báo, không crash trang (rủi ro đã duyệt) | Toàn | Khang | 0.5 | Test với cú pháp lỗi |

**Gate G4 (feature freeze):** FR0–FR4 chạy end-to-end; backend + frontend test pass; lint/build pass; từ đây không thêm chức năng.

**Tiến độ Sprint 4 — phần của Khang (cập nhật 2026-11-10):**

| Task | Trạng thái |
|---|---|
| S4-07 | Xong: thêm `tests/api/test_formula_regions.py`, `test_formula_submit.py`, `tests/worker/test_pdf_pipeline.py`; toàn bộ suite 179 test pass (3 test cần PostgreSQL/Redis tạm). Bỏ thử logic ghi đè `latex_raw` và kiểm tra bounds thì test tương ứng fail. Bằng chứng truy vết ở mục 7 |
| S4-08 | Cần Toàn; chưa làm |
| S4-01…S4-06, S4-09, S4-10 | Việc của Toàn, chưa làm |
### Sprint 5 (tuần 9–10) — Đánh giá chất lượng

| ID | Task | Owner | Reviewer | PD | Sản phẩm/nghiệm thu |
|---|---|---|---|---|---|
| S5-01 | Manifest dữ liệu: mã tài liệu, số trang, loại (scan/vector/nhiều cột/inline/display), số bbox & LaTeX chuẩn đã review | Toàn | Khang | 3 | Manifest có provenance/quyền dùng |
| S5-02 | Đo detector: precision/recall theo IoU đã chọn | Toàn | Khang | 2 | Script/ghi chú tái lập |
| S5-03 | Đo OCR: exact match, edit distance, BLEU giữa `latex_raw` và `latex_final` (hoặc LaTeX chuẩn) trên crop chuẩn | Toàn | Khang | 2 | Bảng kết quả |
| S5-04 | Đo latency cold/warm, RAM/VRAM, tỉ lệ lỗi theo cấu hình đã chốt ở S2-05 | Khang | Toàn | 2 | Bảng đo thật |
| S5-05 | Tổng hợp ví dụ OCR sai và giới hạn; ngưỡng chấp nhận (**D-04**) | Toàn | Khang | 1 | Mục "Hạn chế" cho báo cáo |
| S5-06 | Sửa lỗi blocker có bằng chứng từ đánh giá (không thêm chức năng) | Khang | Toàn | 2 | PR nhỏ, test hồi quy |

**Gate G5:** báo cáo đánh giá tái lập được. Không tuyên bố accuracy nếu chưa có dữ liệu phù hợp.

**Tiến độ Sprint 5 — phần của Khang (cập nhật 2026-11-10):**

| Task | Trạng thái |
|---|---|
| S5-04 | Xong bằng cấu hình CPU đã chốt: latency cold/warm, RAM, tỉ lệ lỗi vận hành trên 4 lần chạy thật (558 vùng, 0 lỗi); bảng ở [ARCHITECTURE](ARCHITECTURE.md). Chưa đo VRAM vì chưa có GPU |
| S5-06 | Chưa làm: cần kết quả đánh giá của S5-01…S5-03 (Toàn) để biết lỗi nào đáng sửa |
| S5-01, S5-02, S5-03, S5-05 | Việc của Toàn, chưa làm |
### Sprint 6 (tuần 11–12) — Báo cáo, demo, bảo vệ

| ID | Task | Owner | Reviewer | PD | Sản phẩm/nghiệm thu |
|---|---|---|---|---|---|
| S6-01 | Báo cáo đồ án theo mẫu của khoa (**D-05**); chương phân tích/kiến trúc/triển khai | Toàn | Khang | 5 | Bản nháp đủ chương |
| S6-02 | Sơ đồ: use case, kiến trúc, sequence upload→OCR→Submit, ER, triển khai | Khang | Toàn | 2 | Khớp code và ARCHITECTURE |
| S6-03 | Ma trận truy vết SRS → code → test (mục 7) hoàn chỉnh | Toàn | Khang | 1.5 | Không còn yêu cầu thiếu test |
| S6-04 | Slides và kịch bản demo (PDF được phép dùng) | Toàn | Khang | 2 | Script demo từng bước |
| S6-05 | Setup/runbook: người khác clone và chạy được từ README/SETUP | Khang | Toàn | 1.5 | Thành viên còn lại tự chạy thành công |
| S6-06 | Tag phiên bản nộp; kiểm tra không có secret/upload/weights trong Git | Khang | Toàn | 0.5 | `git ls-files` sạch |
| S6-07 | Diễn tập bảo vệ ≥ 2 lần; danh sách câu hỏi dự kiến và hạn chế | Khang + Toàn | nhau | 1.5 | Biên bản diễn tập |
| S6-08 | Dự phòng sửa lỗi/chỉnh báo cáo | Khang + Toàn | nhau | 3 | — |

**Gate G6 = điểm dừng đồ án.** Chi tiết ở mục 8.

## 5. Quy trình hằng tuần

- Đầu tuần: chọn task từ sprint, xác nhận owner/reviewer. Giữa tuần: đồng bộ blocker 15 phút. Cuối tuần: demo nội bộ và cập nhật trạng thái task.
- Mỗi PR một luồng nhỏ, ghi FR, test đã chạy, migration (nếu có), ảnh UI (nếu đổi UX) — theo [GIT_WORKFLOW](GIT_WORKFLOW.md) và [CONTRIBUTING](CONTRIBUTING.md).
- Đổi phạm vi: ghi vào mục 9, hai thành viên đồng ý rồi mới sửa SRS và lịch.

## 6. Rủi ro

| Rủi ro | Ảnh hưởng | Giảm thiểu | Owner |
|---|---|---|---|
| Thiếu PDF có quyền dùng | Không đo được accuracy | Bắt đầu xin từ S1-04; nếu thiếu, báo cáo ghi rõ chưa có dataset, không dùng dữ liệu tổng hợp để kết luận accuracy | Toàn |
| GPU/ONNX CUDA không chạy | Chậm | S2-05; CPU fallback có giới hạn rõ, đo latency thật | Khang |
| OCR sai công thức phức tạp | Chất lượng | Giữ bước người dùng rà; ghi ví dụ sai ở S5-05 | Toàn |
| Pix2Text/pix2tex tải model chậm/lần đầu | Demo lỗi | Ghi cold/warm latency; chạy warm-up trước demo | Khang |
| Một người nghỉ/quá tải | Trễ gate | Mỗi task có reviewer biết ngữ cảnh; S6-08 là buffer | Cả hai |
| Đổi contract muộn | Vỡ UI/test | Contract khóa ở G1; đổi phải cập nhật SRS cùng PR | Cả hai |

## 7. Ma trận truy vết

Cập nhật ngày 2026-11-10 từ mã nguồn và test hiện có (24 test backend, chưa có test frontend/worker). "Khoảng trống" là chỗ chưa có test; task đóng khoảng trống nằm ở cột cuối.

| ID | Code chính | Test hiện có | Khoảng trống → task |
|---|---|---|---|
| FR0-01 | `api/auth.py`, `schemas/auth.py` | `test_register_login_logout_and_password_hash` (trùng username → 409), `test_security.py` (kiểm tra credentials) | — |
| FR0-02 | `core/security.py` | Cùng test trên: hash bắt đầu `$argon2`, response không có `password_hash`; `test_passwords_and_tokens_are_never_logged` | — |
| FR0-03 | `core/security.py`, `api/auth.py` | `tests/api/test_auth_hardening.py` (cờ cookie, token hết hạn/giả mạo/alg none/đổi secret, giới hạn đăng nhập, Origin), `test_access_token_has_user_subject_and_expiration` | — |
| FR0-04 | `api/auth.py` | Logout rồi `/me` trả 401 | — |
| FR0-05 | `api/documents.py` (`_get_owned_document`) | `test_document_is_visible_only_to_owner`, `test_other_users_document_is_404_everywhere`, `test_orphan_document_is_not_visible` | — |
| FR1-01 | `api/documents.py` upload | `test_upload_records_size_and_returns_document_id`, `tests/api/test_upload_validation.py` | — |
| FR1-02 | `core/queue.py`, upload/recognize | `tests/api/test_ocr_queue.py`, `test_ocr_queue_concurrency.py` (PostgreSQL), `tests/worker/` | — |
| FR1-03 | `services/pdf_pages.py`, `services/formula_regions.py` | `tests/worker/test_pdf_pipeline.py` (detector giả: trang đánh số từ 1, trang không có công thức, detector lỗi → `processing_failed`), `test_ocr_and_pdf_jobs.py`; chạy thật 17 trang (S1-07) | Test tự động với model MFD thật (chỉ chạy tay) |
| FR1-04 | `models/formula_entry.py`, `services/formula_regions.py` | `test_pdf_pipeline.py` (bbox nằm trong ảnh, crop đúng kích thước bbox, box ngoài trang bị bỏ), `tests/api/test_formula_regions.py` (crop khớp bbox) | — |
| FR1-05 | `api/formulas.py` | `tests/api/test_formula_regions.py` (tạo/sửa/xóa, bounds hợp lệ/ngoài trang/âm, chỉ vùng `proposed`, đúng owner, crop được tạo lại/xóa) | UI pointer/keyboard → S4-03 (Toàn) |
| FR1-06 | `services/formula_ocr.py` | `tests/worker/` (fake model: thành công, lỗi từng công thức, lỗi nạp model, không đụng công thức không `ocr_queued`) | — |
| FR2-01 | `frontend/src/App.jsx` | Chưa có test frontend | S4-01, S4-02 |
| FR2-02 | `App.jsx` (`FormulaEditor`) | Chưa có | S4-02, S4-10 |
| FR2-03 | `App.jsx` (overlay pointer/keyboard) | Chưa có | S4-03, S4-06 |
| FR3-01 | `POST …/formulas/{id}/submit` | `tests/api/test_formula_submit.py` (ghi `latex_final`, chưa OCR → 409, giới hạn độ dài, đúng owner, ghi log) | UI → S4-04 (Toàn) |
| FR3-02 | Cùng endpoint | `test_formula_submit.py` (`latex_raw` không đổi kể cả resubmit; bỏ dòng bảo vệ thì 3 test fail) | — |
| FR3-03 | `GET …/formulas` | `test_submit_is_logged_and_persists_across_reload` | UI reload → S4-04 (Toàn) |
| FR4-01 | `GET /documents`, `GET/DELETE /documents/{id}` | `test_list_*`, `test_get_document_detail_and_log`, `test_delete_removes_rows_and_files`, `test_delete_succeeds_when_files_already_missing` | UI lịch sử → S4-05 |
| FR4-02 | `GET …/source` | `test_download_source_pdf`, `…_missing_file_is_404` | — |
| FR4-03 | `GET …/export` | `test_export_contains_only_submitted_latex_final`, `test_export_without_submitted_formula_is_409` | — |
| FR4-04 | `BUSY_STATUSES` trong `documents.py` | `test_delete_is_blocked_while_processing` | — |
| NFR-01 | models + Compose | Gián tiếp qua test API | — |
| NFR-02 | `alembic/versions/*` | Drill thủ công S1-02 (ghi trong DATABASE.md) | Tự động hóa không bắt buộc |
| NFR-03 | `services/formula_regions.py`, Compose | Kiểm worker S1-06: đang CPU | Chốt cấu hình → S2-05 |
| NFR-04 | — | Có dữ liệu ([DATASET](DATASET.md)), chưa có manifest/đáp án chuẩn | S5-01…S5-05 |
| NFR-05 | `services/action_log.py`, `core/security.py` | `test_passwords_and_tokens_are_never_logged` | — |
| NFR-06 | `core/queue.py`, `services/formula_ocr.py`, `services/pdf_pages.py` | `test_ocr_queue*.py`, `tests/worker/`; drill restart worker/Redis (ARCHITECTURE) | Mất dữ liệu Redis, job quá hạn trên UI |
| NFR-07 | `core/limits.py`, `services/upload_validation.py` | `tests/api/test_upload_validation.py`, `tests/unit/test_sanitize_filename.py`, `tests/worker/` (job từ chối file quá giới hạn) | — |
## 8. Definition of Done của đồ án (điểm dừng)

Đồ án hoàn thành khi **tất cả** điều kiện sau đúng:

1. FR0–FR4 chạy end-to-end từ clone sạch bằng README/SETUP; phạm vi ngoài SRS §5 không được tuyên bố là đã có. Mọi hạng mục bắt buộc của kế hoạch đã duyệt (mục 2.4, trừ nhóm tuỳ chọn D-10) đều xong hoặc có sai khác được ghi rõ trong báo cáo.
2. `docker compose config -q` pass, 5 service healthy, Alembic ở head, migration kiểm thử từ DB rỗng và DB có dữ liệu.
3. Queue an toàn: enqueue kép, Redis lỗi, worker restart, OCR exception đều có hành vi được test.
4. Chế độ GPU hoặc CPU được chứng minh bằng provider + inference trong worker, ghi rõ trong báo cáo.
5. `latex_raw` không bao giờ bị ghi đè; `latex_final` chỉ đổi qua Submit; có test.
6. Test backend và frontend chạy bằng lệnh tài liệu hóa và pass; `npm run build` + `npm run lint` pass.
7. Báo cáo đánh giá detector/OCR trên dữ liệu có quyền dùng, nêu metric, lỗi phổ biến và hạn chế; không che công thức sai.
8. Ma trận truy vết không có yêu cầu thiếu code/test.
9. Báo cáo, slides, kịch bản demo hoàn tất; cả hai thành viên đã diễn tập ≥ 2 lần.
10. Git không chứa secret, upload, model weights, `.venv`, `node_modules`, `dist`.

## 9. Quyết định cần chủ dự án xác nhận

Không tự chọn các mục dưới đây. Trạng thái mặc định được ghi để lịch vẫn chạy được.

| ID | Câu hỏi | Mặc định khi chưa quyết | Hạn |
|---|---|---|---|
| D-01 | Có đưa Role Admin, reset mật khẩu/xác minh email, upload ảnh đơn lẻ vào phạm vi? | Không (giữ ngoài phạm vi) | Hết S2 |
| D-09 | Kế hoạch đã duyệt ghi `POST /documents/{id}/process` đồng bộ; code dùng xử lý nền. Giữ code hiện tại và cập nhật contract trong tài liệu nộp, hay thêm endpoint `/process` tương thích? | Giữ code hiện tại; ghi chú sai khác ở báo cáo | Hết S1 |
| D-10 | Có làm hướng mở rộng tuỳ chọn (Texo, dots.ocr/GLM-OCR, Mathpix/VLM làm backend thứ hai, WebSocket tiến trình) không? Mỗi mục cần quyết định riêng và kiểm chứng tính khả thi trước khi vào lịch | Không làm | Hết S3 |
| D-02 | Test runner frontend nào? | Chưa chọn; dùng checklist thủ công cho tới khi chốt | Đầu S3 |
| D-03 | Cách rate limit đăng nhập (thư viện hay tự viết)? | Chưa thêm dependency | Đầu S3 |
| D-04 | Ngưỡng accuracy/IoU chấp nhận được? | Chỉ báo cáo số đo, không đặt ngưỡng | Đầu S5 |
| D-05 | Cấu trúc/mẫu báo cáo của khoa | Chưa có; chương đề xuất ở S6-01 phải đối chiếu mẫu | Đầu S5 |
| D-06 | Demo chỉ chạy local Compose hay cần server demo? | Chỉ local Compose | Đầu S5 |
| D-07 | Document cũ `uploaded_by IS NULL` xử lý thế nào? | Không hiện cho ai | Đầu S3 |
| D-08 | MSSV, lớp/môn, GVHD, nhóm trưởng, ngày nộp | Để trống trong TEAM | Sớm nhất |

## 10. Checklist trước bảo vệ

- [ ] `docker compose config -q`; toàn bộ service healthy; Alembic head đúng.
- [ ] Dữ liệu smoke test không làm bẩn DB demo.
- [ ] Redis AOF/queue kiểm tra sau restart.
- [ ] GPU inference pass hoặc CPU fallback được ghi rõ.
- [ ] PDF nhiều trang hợp lệ chạy hết render/detect/OCR; trường hợp hỏng/mã hóa bị từ chối đúng.
- [ ] Bbox pointer + keyboard và crop refresh hoạt động.
- [ ] MathLive font local và đồng bộ hai chiều pass.
- [ ] Submit chỉ sửa `latex_final`; `latex_raw` nguyên; export `.tex` đúng nội dung đã Submit.
- [ ] Retry/failure path và toàn bộ test suite chạy.
- [ ] Báo cáo, slides, demo script, TEAM metadata được cả hai review.
- [ ] Máy demo đã warm-up model; có video dự phòng nếu runtime lỗi.
