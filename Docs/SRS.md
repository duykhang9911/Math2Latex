# Software Requirements Specification

## 1. Mục đích/phạm vi

Ứng dụng chuyển công thức trong PDF thành LaTeX có thể chỉnh sửa. Detector chỉ đề xuất vùng; người dùng rà trước OCR. OCR không được xem là ground truth.

Mỗi yêu cầu có ID dạng `FRn-mm`/`NFR-mm` để truy vết sang task và test trong [PHAN_CONG_CONG_VIEC](PHAN_CONG_CONG_VIEC.md) §7. FR1–FR3 tương ứng FR1–FR3 của kế hoạch đã duyệt; FR0 và FR4 là phần bổ sung.

## 2. Actor

- Người dùng: upload PDF, rà/sửa vùng, sửa công thức, Submit.
- API: validate request, quản lý state và ghi dữ liệu.
- Worker: render, detect, OCR các job từ queue.
- Vận hành: quản lý PostgreSQL, Redis, worker và model runtime.

## 3. Functional requirements

### FR0 — Tài khoản và quyền sở hữu dữ liệu

| ID | Yêu cầu |
|---|---|
| FR0-01 | Người dùng đăng ký bằng username duy nhất và mật khẩu đạt chính sách tối thiểu. |
| FR0-02 | Backend chỉ lưu password hash Argon2; không trả hash hoặc mật khẩu trong response/log. |
| FR0-03 | Đăng nhập tạo access token JWT ngắn hạn trong cookie HttpOnly, SameSite=Lax. |
| FR0-04 | Người dùng đăng xuất để xóa cookie phiên. |
| FR0-05 | Document mới gắn `uploaded_by`; các API đọc/sửa/xóa document/formula chỉ cho owner truy cập. |

**Acceptance:** username trùng không tạo account; mật khẩu sai trả lỗi chung; token hết hạn/giả mạo bị từ chối; user A không truy cập document user B; password hash/token không xuất hiện trong response.

### FR1 — PDF → formula proposals → `latex_raw`

| ID | Yêu cầu |
|---|---|
| FR1-01 | Upload PDF tạo document UUID và lưu file nguồn. |
| FR1-02 | API enqueue xử lý nền, không chờ OCR trong request. |
| FR1-03 | Worker render từng trang bằng PyMuPDF, Pix2Text MFD đề xuất bbox theo pixel. |
| FR1-04 | Lưu page image, crop, bbox, confidence và formula status. |
| FR1-05 | Người dùng thêm/di chuyển/resize/xóa vùng trước khi OCR. |
| FR1-06 | Sau xác nhận, pix2tex đọc crop; output ghi `latex_raw`. |

**Acceptance:** page number bắt đầu từ 1; crop khớp bbox; bbox luôn trong ảnh; trang rỗng trả danh sách rỗng; lỗi có trạng thái; job đã enqueue tồn tại qua restart theo queue policy.

### FR2 — Chỉnh sửa 2 chiều

| ID | Yêu cầu |
|---|---|
| FR2-01 | LaTeX textarea và MathLive dùng chung giá trị state. |
| FR2-02 | Thay đổi ở editor này cập nhật editor kia. |
| FR2-03 | Chỉnh vùng bằng pointer và keyboard; edit LaTeX chưa Submit chỉ là tạm trên UI. |

**Acceptance:** đồng bộ hai chiều; accessible focus/instructions; keyboard arrows move, Alt+arrows resize, Shift dùng bước 10 px; font MathLive được tải local.

### FR3 — Submit → database

| ID | Yêu cầu |
|---|---|
| FR3-01 | Submit từng formula ghi nội dung hiện tại vào `latex_final`. |
| FR3-02 | `latex_raw` không đổi. |
| FR3-03 | Reload trả lại raw/final/status đã lưu. |

**Acceptance:** chưa OCR thì Submit bị từ chối; lỗi API không hiển thị đã lưu; resubmit có behavior nhất quán.

### FR4 — Lịch sử tải lên và xuất kết quả

| ID | Yêu cầu |
|---|---|
| FR4-01 | Người dùng xem danh sách document của mình (mới nhất trước, có phân trang), mở lại, xóa. |
| FR4-02 | Tải lại PDF gốc. |
| FR4-03 | Xuất file `.tex` chỉ gồm công thức đã Submit (`latex_final`). |
| FR4-04 | Không cho xóa document đang `processing_pages`, `detecting_formulas` hoặc `ocr_processing`. |

**Acceptance:** user A không thấy/xóa/tải document của user B; export không chứa `latex_raw`; export khi chưa Submit trả lỗi rõ; xóa dọn cả bản ghi database và thư mục file.

## 4. Non-functional requirements

| ID | Yêu cầu |
|---|---|
| NFR-01 | PostgreSQL giữ metadata/LaTeX; filesystem/object storage giữ file; Redis giữ queue state. |
| NFR-02 | Mọi schema change có Alembic revision mới; migration kiểm thử từ DB rỗng và DB có dữ liệu. |
| NFR-03 | GPU là tùy chọn; kiểm tra provider và inference thật. CPU fallback phải rõ ràng. |
| NFR-04 | Đánh giá accuracy trên PDF đại diện có quyền sử dụng; ghi rõ dataset/metric. |
| NFR-05 | Không ghi credentials hoặc nội dung nhạy cảm vào log. |
| NFR-06 | Queue an toàn: không enqueue kép, job retry-safe, có timeout và cách phục hồi `ocr_queued` bị treo. |
| NFR-07 | Upload có giới hạn server-side (kích thước, số trang, pixel, timeout) và validate nội dung PDF. |

## 5. Ngoài phạm vi/chưa nghiệm thu

Admin/role management, reset password, xác minh email, pipeline ảnh đơn lẻ, OCR text toàn trang, collaborative editing và production SLA chưa được nghiệm thu.
