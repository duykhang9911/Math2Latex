# Báo cáo tuần 1 - Math2Latex

## 1. Mục tiêu tuần 1

Tuần 1 tập trung vào việc chuẩn bị môi trường phát triển và xây dựng nền tảng ban đầu cho dự án Math2Latex. Mục tiêu chính là:

- Khởi tạo và chạy thành công hệ thống backend, frontend và database
- Hiểu rõ cấu trúc dự án
- Kiểm tra được API health check và frontend hoạt động bình thường
- Chuẩn bị nền tảng cho các chức năng chính của dự án trong các tuần tiếp theo

---

## 2. Nội dung đã thực hiện

### 2.1. Thiết lập dự án

- Khởi tạo cấu trúc dự án với các folder chính: backend, frontend, database
- Cấu hình Docker Compose để chạy đồng thời các service
- Thiết lập backend bằng FastAPI
- Thiết lập frontend bằng React + Vite
- Thiết lập PostgreSQL làm database

### 2.2. Cấu hình môi trường

Dự án đã được cấu hình thông qua file:

- `docker-compose.yml`
- `backend/requirements.txt`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `frontend/package.json`

### 2.3. Kiểm tra hệ thống

- Backend đã chạy thành công trên port 8000
- Frontend đã chạy thành công trên port 5173
- Database PostgreSQL đã khởi động thành công trên port 5432
- API kiểm tra sức khỏe `/health` trả về kết quả:

```json
{"status":"ok"}
```

---

## 3. Kết quả đạt được

### 3.1. Backend

- FastAPI đã hoạt động đúng
- Route `/health` chạy thành công
- Backend có thể bắt đầu và phục vụ request từ frontend

### 3.2. Frontend

- React + Vite đã khởi động thành công
- Trang demo của React có thể hiển thị trên localhost
- Dự án đã sẵn sàng để phát triển giao diện người dùng

### 3.3. Database

- PostgreSQL đã chạy ổn định
- Cơ sở dữ liệu đã sẵn sàng cho việc lưu trữ thông tin sau này

---

## 4. Những kiến thức đã học được

Trong tuần 1, em đã nắm được các kiến thức cơ bản sau:

- Cấu trúc của một dự án web full-stack
- Cách tổ chức project theo backend/frontend/database
- Cách khởi động ứng dụng bằng Docker Compose
- Cách truy cập và kiểm tra API backend
- Cách đọc và hiểu file cấu hình Docker
- Cách làm quen với FastAPI và React

---

## 5. Khó khăn và cách khắc phục

### Khó khăn

- Cần làm quen với cách triển khai multi-service bằng Docker
- Cần hiểu rõ các port và dependency giữa backend, frontend và database
- Cần nắm được cách kiểm tra log khi service không chạy

### Cách khắc phục

- Đọc kỹ file `docker-compose.yml`
- Chạy từng service và kiểm tra port tương ứng
- Dùng lệnh `docker compose up --build` để kiểm tra trạng thái dịch vụ
- Kiểm tra API health check và log của container để tìm lỗi

---

## 6. Kết luận

Tuần 1 đã hoàn thành tốt về mặt nền tảng. Dự án đã được dựng thành công, backend và frontend đã chạy đúng, database đã sẵn sàng. Đây là bước đầu rất quan trọng để phát triển các chức năng chính của Math2Latex trong các tuần tiếp theo.

Việc cần làm tiếp theo là chuyển từ giai đoạn chuẩn bị sang giai đoạn phát triển chức năng: upload file PDF, xử lý OCR, trích xuất công thức toán và chuyển đổi sang LaTeX.

---

## 7. Kế hoạch cho tuần 2

Tuần 2 sẽ tập trung vào:

- Tạo giao diện upload file PDF/ảnh
- Xây dựng API upload file ở backend
- Lưu file vào thư mục uploads
- Kiểm tra dữ liệu đầu vào từ frontend
- Chuẩn bị nền tảng cho OCR và xử lý công thức toán
