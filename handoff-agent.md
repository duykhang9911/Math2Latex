# Handoff Agent - Math2Latex

## 1. Tóm tắt dự án

Math2Latex là dự án chuyển đổi công thức toán từ ảnh/PDF sang LaTeX. Dự án hiện đang theo kiến trúc full-stack:

- Backend: Python + FastAPI
- Frontend: React + Vite
- Database: PostgreSQL
- Môi trường: Docker Compose

---

## 2. Trạng thái hiện tại

### Đã hoàn thành

- Dự án đã được khởi tạo và chạy thành công bằng Docker
- Backend health check hoạt động
- Frontend chạy thành công trên localhost:5173
- PostgreSQL chạy thành công trên localhost:5432
- Chức năng upload file cơ bản đã được xây dựng và kiểm tra thành công
- File upload được lưu vào thư mục backend/uploads
- Backend hỗ trợ CORS để frontend có thể gọi API

### Đã sửa trong code

- [backend/app/main.py](backend/app/main.py)
  - thêm route `/health`
  - thêm route `/upload`
  - lưu file vào thư mục uploads
  - kiểm tra định dạng file
  - trả về JSON phản hồi

- [backend/requirements.txt](backend/requirements.txt)
  - thêm `python-multipart`

- [frontend/src/App.jsx](frontend/src/App.jsx)
  - thay giao diện demo mặc định bằng giao diện upload file
  - xử lý chọn file và gửi lên backend
  - hiển thị trạng thái upload

- [frontend/src/App.css](frontend/src/App.css)
  - viết lại CSS cho giao diện upload

- [backend/uploads](backend/uploads)
  - thư mục lưu file upload

---

## 3. Kiểm tra đã chạy thành công

Các lệnh / kiểm tra đã thực hiện thành công:

- `docker compose up --build -d`
- `curl` hoặc script upload file thực tế tới backend
- Kết quả upload mẫu:

```json
{"status":"uploaded","filename":"valid-upload.png","size":70,"path":"/app/uploads/valid-upload.png"}
```

Điều này chứng minh:

- backend đang chạy
- upload endpoint hoạt động
- file được lưu đúng vị trí

---

## 4. Công việc đang chờ tiếp tục

### Tuần 3 nên làm

1. OCR / nhận dạng văn bản và công thức từ file upload
2. Xử lý file PDF hoặc ảnh đầu vào
3. Tạo service xử lý ở backend
4. Trích xuất nội dung thành text hoặc cấu trúc dễ xử lý
5. Chuẩn chuyển sang bước chuyển đổi công thức toán thành LaTeX

### Gợi ý thiết kế tiếp theo

- Backend nên có một service riêng như:
  - `services/ocr_service.py`
  - `services/math_parser.py`
  - `services/file_service.py`

- Frontend nên có:
  - form upload
  - hiển thị trạng thái xử lý
  - khu vực preview file
  - khu vực hiển thị kết quả LaTeX

---

## 5. Mục tiêu tiếp theo của agent tiếp nối

Agent tiếp theo nên tập trung vào:

- xử lý ảnh/PDF sau upload
- OCR text và công thức toán
- chuyển đổi sang LaTeX
- hiển thị kết quả cho người dùng trên frontend
- tối ưu payload và error handling

---

## 6. Các file quan trọng cần xem trước

- [backend/app/main.py](backend/app/main.py)
- [backend/requirements.txt](backend/requirements.txt)
- [frontend/src/App.jsx](frontend/src/App.jsx)
- [frontend/src/App.css](frontend/src/App.css)
- [docker-compose.yml](docker-compose.yml)
- [tuan1.md](tuan1.md)
- [tuan2.md](tuan2.md)
- [week2-process.md](week2-process.md)

---

## 7. Ghi chú quan trọng

- Đây là dự án đang trong giai đoạn phát triển ban đầu, chưa có OCR hoàn chỉnh
- Upload file đã được chứng minh hoạt động
- Cần tiếp tục xây dựng bước xử lý dữ liệu sau upload
- Nếu agent mới làm tiếp, nên bắt đầu từ route upload và service xử lý file

---

## 8. Đề xuất bắt đầu nhanh

Agent mới nên bắt đầu với các bước sau:

1. Đọc [backend/app/main.py](backend/app/main.py)
2. Xác định nơi sẽ thêm service OCR
3. Tạo endpoint mới: `/process`
4. Nhận đường dẫn file đã upload
5. Tạo logic OCR hoặc xử lý văn bản
6. Trả về kết quả JSON dạng:

```json
{"status":"success","latex":"x^2 + y^2 = 1"}
```

---

## 9. Kết luận

Dự án đã hoàn thành phần nền tảng upload file thành công và sẵn sàng cho giai đoạn xử lý OCR / chuyển đổi LaTeX. Agent tiếp theo nên bắt đầu từ đây để phát triển nghiệp vụ chính của hệ thống.
