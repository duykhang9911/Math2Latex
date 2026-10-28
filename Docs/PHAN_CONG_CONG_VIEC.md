# Kế hoạch hoàn thành Math2Latex — nhóm 2 thành viên

## 1. Nhân sự và nguyên tắc

- **Đoàn Trương Duy Khang — Owner Backend/Platform:** API, PostgreSQL/Alembic, Redis/RQ, Docker/GPU, xử lý PDF/MFD/OCR.
- **Ngô Hồ Tuấn Toàn — Owner Frontend/QA/Docs:** React/MathLive, accessibility, browser test, dữ liệu đánh giá được phép dùng, tài liệu/demo.
- Hai người review chéo contract API, trạng thái, bbox và kết quả demo. MSSV, deadline và nhóm trưởng chưa được cung cấp nên chưa ghi.
- Effort là **người-ngày (PD)** ước lượng, cần nhóm điều chỉnh theo lịch môn học. Các việc có thể chạy song song sau khi chốt contract.

## 2. Hiện trạng đầu vào

- Đã có upload PDF, render trang, MFD proposals, crop, sửa vùng chuột/keyboard, pix2tex OCR, MathLive/LaTeX, Submit, migration và API.
- Đang bổ sung đăng ký/đăng nhập Argon2/JWT cookie và owner scoping cho document APIs; migration ownership cần apply trên môi trường hiện tại.
- Source/config có Redis/RQ, Redis AOF volume, worker GPU reservation, local MathLive font copy và Node 22.
- Phải chạy/rebuild Compose ở phiên hiện tại để xác nhận thay đổi queue/GPU mới nhất; không lấy container/image cũ làm bằng chứng.
- Không tìm thấy PDF toán thực được phép dùng trong uploads/repository; các PDF trong package `.venv` không phải bộ đánh giá.

## 3. Kế hoạch theo milestone

### M0 — Khởi động stack và xác nhận contract (P0, 0.5–1 ngày)

**Owner:** Khang. **Review:** Toàn.

- Chạy `docker compose config -q`, `docker compose up -d --build`, kiểm tra health `db`, `redis`, `backend`, `worker`, `frontend`.
- Chạy Alembic upgrade; xác nhận API upload enqueue job vào queue `math2latex`.
- Kiểm tra API response/status và frontend polling; ghi version/config thực tế.

**Nghiệm thu:** các service healthy; `/health` trả `ok`; migration ở head; `rq info` nhận worker; upload test tạo document và job được xử lý.

### M1 — Queue bền vững, idempotency và GPU (P0, 2–4 PD)

**Owner:** Khang. **Review:** Toàn.

- Test Redis AOF/volume khi restart Redis/backend/worker.
- Chống enqueue kép cho recognize/retry; rà row lock, job identity, trạng thái khi Redis không nhận job.
- Định nghĩa timeout/retry/failure visibility và cách phục hồi formula `ocr_queued` bị treo khi worker chết.
- Trong worker, kiểm tra `torch.cuda.is_available()`, `onnxruntime.get_available_providers()` và chạy inference thật.
- Nếu ONNX CUDA plugin lỗi: thử `MATH_DETECTOR_BACKEND=pytorch` trên CUDA, ghi latency/VRAM và chọn cấu hình thực sự chạy. Nếu chưa ổn định, chốt CPU fallback có giới hạn rõ.

**Nghiệm thu:** test enqueue kép chỉ tạo một job hợp lệ; worker restart không để state mơ hồ; Redis unavailable trả lỗi retryable; có log provider và inference. Không ghi “GPU pass” chỉ từ `nvidia-smi`.

### M2 — Bộ dữ liệu và đánh giá accuracy (P0/P1, 2–5 PD sau khi có tài liệu)

**Owner:** Toàn. **Hỗ trợ:** Khang.

- Chuẩn bị 5–10 PDF đại diện: scan, vector, nhiều cột, inline/display, nhiều trang; xác nhận quyền sử dụng.
- Lập manifest gồm document code, page count, loại trang, expected bbox/formula count và LaTeX chuẩn đã review.
- Không commit PDF riêng tư vào Git; lưu dữ liệu kiểm thử ở vị trí được nhóm thống nhất.
- Đo detector precision/recall theo IoU threshold đã chọn; OCR exact match/edit distance trên crop chuẩn; cold/warm latency, RAM/VRAM, failure rate.
- Ghi ví dụ OCR sai và khuyến nghị người dùng rà.

**Nghiệm thu:** report tái lập được, có provenance/quyền dùng, baseline metric, lỗi phổ biến và threshold được nhóm/giảng viên thống nhất. Không tuyên bố accuracy nếu chưa có dataset phù hợp.

### M3 — UI/accessibility và browser verification (P1, 1–3 PD)

**Owner:** Toàn. **Review:** Khang.

- Kiểm tra MathLive font local trong Docker Node 22; WOFF2 trả HTTP 200, không console font errors.
- Test LaTeX ↔ MathLive với fraction, root, matrix, Greek và syntax lỗi.
- Keyboard-only: Tab focus bbox, arrows move, Alt+arrows resize, Shift dùng bước 10 px; screen-reader name/help; touch/mobile.
- Test queued/loading/failure/retry/saved/unsaved states và crop refresh sau resize.
- Chỉ code-split MathLive nếu đo được lợi ích và không ảnh hưởng editor.

**Nghiệm thu:** browser test pass desktop/mobile; keyboard và pointer thao tác được; font nội bộ hoạt động sau build/restart.

### M4 — Upload hardening, retention và test tự động (P1, 3–6 PD)

**Owner:** Khang (API/security), Toàn (UI tests/fixtures); review chéo.

- Chốt giới hạn upload bytes, trang PDF, pixel count và processing timeout.
- Validate PDF content/encryption, lỗi malformed; chống filename/path abuse.
- Chốt retention/cleanup cho source, pages, crops, failed jobs và orphan files.
- Hoàn thiện auth: unique username chuẩn hóa, token expiry/secret policy, cookie Secure/CSRF policy khi deploy HTTPS, rate limit login và quy trình với document cũ chưa owner.
- Thêm backend tests cho schemas/bounds/state/API/queue; frontend tests cho editor/overlay/submit. Dùng fake detector/OCR trong unit tests; real GPU test opt-in.

**Nghiệm thu:** giới hạn trả lỗi thân thiện; tests chạy bằng lệnh tài liệu hóa; cleanup không xóa dữ liệu hợp lệ.

### M5 — Báo cáo và demo cuối (P1, 2–4 PD)

**Owner:** Toàn (báo cáo/demo), Khang (sơ đồ backend/runtime); review chéo.

- Trace SRS → implementation → test evidence.
- Cập nhật architecture/sequence/deployment, setup, backlog/known limitations.
- Chuẩn bị demo PDF được phép dùng: upload → sửa bbox → OCR → sửa hai editor → Submit → reload chứng minh `latex_raw`/`latex_final`.
- Ghi rõ provider GPU/CPU, latency và accuracy report; không che các công thức OCR sai.

**Nghiệm thu:** thành viên khác clone/setup và chạy demo được; báo cáo nói rõ phần chưa hoàn thiện.

## 4. Phân công song song

| Giai đoạn | Đoàn Trương Duy Khang | Ngô Hồ Tuấn Toàn | Điểm bàn giao |
|---|---|---|---|
| M0 | Compose, migration, API/queue health | Smoke frontend, kiểm contract UI | document status + formula/page response |
| M1 | Idempotency, worker restart, GPU/provider | Lập test matrix và ghi log/latency | worker behavior + report mẫu |
| M2 | Sửa backend theo lỗi có bằng chứng | Xin PDF, label/ground truth, tính metric | dataset manifest + detector/OCR report |
| M3 | Review API/bbox/crop behavior | Fonts, keyboard, mobile/browser test | acceptance evidence |
| M4 | Limits/security/DB/queue tests | UI tests, fixtures và UX error state | test suite và cleanup policy |
| M5 | Sơ đồ/API/runtime limitations | Báo cáo, slides, kịch bản demo | demo final đã chạy lại |

## 5. Lịch tham khảo 4 tuần

Lịch này là khung gợi ý, không phải deadline cố định. Nếu thời gian ít hơn, giữ thứ tự dependency và giảm scope P2 trước.

| Tuần | Khang | Tuấn Toàn | Mốc cuối tuần |
|---|---|---|---|
| 1 | M0; bắt đầu Q-01; xác minh runtime worker/GPU | Kiểm UI hiện tại; chuẩn bị tiêu chí/data manifest; xin PDF hợp lệ | Stack/queue chạy, biết GPU mode thật |
| 2 | Hoàn tất idempotency/restart; sửa lỗi worker | Thu thập/label PDF; chạy MathLive/font/keyboard/browser checks | Queue ổn định, dataset có ground truth |
| 3 | Upload limits, cleanup, backend tests; hỗ trợ benchmark | MFD/OCR benchmark, frontend tests, UX fixes | Có report accuracy và regression tests |
| 4 | Fix blocker integration, setup/ops notes | Traceability, báo cáo, slides/demo script | Demo E2E và handoff hoàn chỉnh |

## 6. Definition of Done

Mỗi task có owner, reviewer, acceptance criteria, test evidence, files/API/schema affected và fallback. OCR phải được người dùng rà. Nếu thiếu PDF/GPU/quyền truy cập, ghi blocker và người cần cung cấp; không thay dữ liệu thật bằng dữ liệu tổng hợp để tuyên bố accuracy.

## 7. Checklist trước demo cuối

- [ ] `docker compose config -q` và toàn bộ services healthy.
- [ ] Alembic head đúng; dữ liệu smoke test không làm bẩn demo DB.
- [ ] Redis AOF/worker queue được kiểm tra sau restart.
- [ ] GPU inference pass hoặc CPU fallback được ghi rõ.
- [ ] PDF nhiều trang hợp lệ chạy hết render/detect/OCR.
- [ ] Bbox pointer + keyboard và crop refresh hoạt động.
- [ ] MathLive font/2-way sync pass.
- [ ] Submit chỉ sửa `latex_final`; `latex_raw` vẫn nguyên.
- [ ] Retry/failure path và test suite chạy.
- [ ] Báo cáo, TEAM metadata và hướng dẫn demo được cả hai review.
