# Software Requirements Specification

## 1. Mục đích/phạm vi

Ứng dụng chuyển công thức trong PDF thành LaTeX có thể chỉnh sửa. Detector chỉ đề xuất vùng; người dùng rà trước OCR. OCR không được xem là ground truth.

## 2. Actor

- Người dùng: upload PDF, rà/sửa vùng, sửa công thức, Submit.
- API: validate request, quản lý state và ghi dữ liệu.
- Worker: render, detect, OCR các job từ queue.
- Vận hành: quản lý PostgreSQL, Redis, worker và model runtime.

## 3. Functional requirements

### FR0 — Tài khoản và quyền sở hữu dữ liệu

1. Người dùng đăng ký bằng username duy nhất và mật khẩu đạt chính sách tối thiểu.
2. Backend chỉ lưu password hash Argon2; không trả hash hoặc mật khẩu trong response/log.
3. Đăng nhập tạo access token JWT ngắn hạn trong cookie HttpOnly, SameSite=Lax.
4. Người dùng đăng xuất để xóa cookie phiên.
5. Document mới gắn `uploaded_by`; các API đọc/sửa/xóa document/formula chỉ cho owner truy cập.

**Acceptance:** username trùng không tạo account; mật khẩu sai trả lỗi chung; token hết hạn/giả mạo bị từ chối; user A không truy cập document user B; password hash/token không xuất hiện trong response.

### FR1 — PDF → formula proposals → `latex_raw`

1. Upload PDF tạo document UUID và lưu file nguồn.
2. API enqueue xử lý nền, không chờ OCR trong request.
3. Worker render từng trang bằng PyMuPDF, Pix2Text MFD đề xuất bbox theo pixel.
4. Lưu page image, crop, bbox, confidence và formula status.
5. Người dùng thêm/di chuyển/resize/xóa vùng trước khi OCR.
6. Sau xác nhận, pix2tex đọc crop; output ghi `latex_raw`.

**Acceptance:** page number bắt đầu từ 1; crop khớp bbox; bbox luôn trong ảnh; trang rỗng trả danh sách rỗng; lỗi có trạng thái; job đã enqueue tồn tại qua restart theo queue policy.

### FR2 — Chỉnh sửa 2 chiều

- LaTeX textarea và MathLive dùng chung giá trị state.
- Thay đổi ở editor này cập nhật editor kia.
- Chỉnh vùng bằng pointer và keyboard; edit LaTeX chưa Submit chỉ là tạm trên UI.

**Acceptance:** đồng bộ hai chiều; accessible focus/instructions; keyboard arrows move, Alt+arrows resize, Shift dùng bước 10 px; font MathLive được tải local.

### FR3 — Submit → database

- Submit từng formula ghi nội dung hiện tại vào `latex_final`.
- `latex_raw` không đổi.
- Reload trả lại raw/final/status đã lưu.

**Acceptance:** chưa OCR thì Submit bị từ chối; lỗi API không hiển thị đã lưu; resubmit có behavior nhất quán.

## 4. Non-functional requirements

- PostgreSQL giữ metadata/LaTeX; filesystem/object storage giữ file; Redis giữ queue state.
- Mọi schema change có Alembic revision mới.
- GPU là tùy chọn; kiểm tra provider và inference thật. CPU fallback phải rõ ràng.
- Đánh giá accuracy trên PDF đại diện có quyền sử dụng; ghi rõ dataset/metric.
- Không ghi credentials hoặc nội dung nhạy cảm vào log.

## 5. Ngoài phạm vi/chưa nghiệm thu

Admin/role management, reset password, xác minh email, pipeline ảnh đơn lẻ, OCR text toàn trang, collaborative editing và production SLA chưa được nghiệm thu.