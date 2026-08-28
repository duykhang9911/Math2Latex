# Báo cáo tuần 2 - Math2Latex

## 1. Mục tiêu tuần 2

Tuần 2 tập trung vào việc xây dựng chức năng upload file đầu tiên của hệ thống. Mục tiêu chính là cho phép người dùng tải lên ảnh hoặc PDF chứa công thức toán từ giao diện frontend, backend nhận file và lưu vào thư mục uploads để chuẩn bị cho các bước xử lý tiếp theo.

---

## 2. Nội dung đã thực hiện

### 2.1. Backend

- Thêm route upload file trong FastAPI
- Kiểm tra định dạng file hợp lệ
- Lưu file vào thư mục `backend/uploads`
- Trả về JSON chứa thông tin file đã upload
- Cấu hình CORS để frontend có thể gọi API từ localhost khác port

### 2.2. Frontend

- Thay giao diện mặc định của React/Vite bằng giao diện upload file
- Tạo form chọn file và nút upload
- Gửi dữ liệu file lên backend bằng `FormData`
- Hiển thị trạng thái upload và thông tin file sau khi upload thành công

### 2.3. Cấu hình môi trường

- Thêm dependency `python-multipart` để FastAPI hỗ trợ xử lý upload form-data
- Kiểm tra lại Docker Compose để đảm bảo backend và frontend chạy đúng cùng lúc

---

## 3. Kết quả đạt được

- Hệ thống upload file hoạt động thành công
- Backend nhận file và lưu vào thư mục uploads
- Frontend có thể gửi file lên server
- API trả về kết quả dạng JSON xác nhận file đã được upload

---

## 4. Kiểm tra thực tế

Sau khi chạy lại Docker và gửi một file PNG hợp lệ lên API, kết quả trả về là:

```json
{"status":"uploaded","filename":"valid-upload.png","size":70,"path":"/app/uploads/valid-upload.png"}
```

Kết quả này chứng minh chức năng upload đã hoạt động đúng theo yêu cầu của tuần 2.

---

## 5. Khó khăn và cách giải quyết

### Khó khăn

- FastAPI không hỗ trợ upload form-data nếu chưa cài `python-multipart`
- Frontend và backend chạy ở hai port khác nhau nên cần CORS

### Giải quyết

- Thêm `python-multipart` vào file requirements
- Cấu hình CORS trong FastAPI
- Kiểm tra lại log container và test upload bằng file thật

---

## 6. Kết luận

Tuần 2 đã hoàn thành tốt phần nền tảng chức năng upload file. Dự án từ trạng thái “chạy được” đã tiến lên thành “có thể nhận dữ liệu đầu vào từ người dùng”. Đây là bước quan trọng để tiếp tục thực hiện OCR và chuyển đổi công thức toán sang LaTeX ở các tuần tiếp theo.
