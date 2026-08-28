# Tuần 1 - Math2Latex

## Mục tiêu tuần 1

Tuần 1 tập trung vào việc chuẩn bị môi trường phát triển và xây dựng nền tảng ban đầu cho dự án Math2Latex. Mục tiêu chính là:

- Khởi tạo và chạy thành công backend, frontend và database
- Hiểu cấu trúc dự án
- Xây dựng được API cơ bản và giao diện demo đầu tiên
- Chuẩn bị nền tảng cho các tuần sau: upload PDF, OCR, chuyển đổi công thức toán thành LaTeX

---

## 1. Hiểu dự án

Dự án này gồm 3 phần chính:

1. Backend
   - Dùng Python + FastAPI
   - Chịu trách nhiệm xử lý API, upload file, OCR, chuyển đổi công thức toán

2. Frontend
   - Dùng React + Vite
   - Chịu trách nhiệm giao diện người dùng

3. Database
   - Dùng PostgreSQL
   - Lưu trữ dữ liệu, logs, hoặc metadata của file

---

## 2. Cấu trúc dự án hiện tại

```text
Math2Latex/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── README.md (nếu có)
```

---

## 3. Công việc cần làm trong tuần 1

### Bước 1: Khởi động môi trường

Chạy lệnh sau ở thư mục gốc dự án:

```bash
docker compose up --build
```

Nếu chạy thành công, bạn sẽ thấy:

- backend đang chạy trên port 8000
- frontend đang chạy trên port 5173
- PostgreSQL đang chạy trên port 5432

### Bước 2: Kiểm tra backend

Mở browser hoặc chạy lệnh:

```bash
curl http://localhost:8000/health
```

Kết quả mong đợi:

```json
{"status":"ok"}
```

Nếu endpoint này trả về đúng, backend đang hoạt động tốt.

### Bước 3: Kiểm tra frontend

Mở trình duyệt:

```text
http://localhost:5173
```

Nếu giao diện load được, frontend đã chạy ổn.

### Bước 4: Hiểu file backend chính

File cần đọc trước:

- backend/app/main.py

Nội dung hiện tại cơ bản là một FastAPI app và route kiểm tra sức khỏe:

```python
from fastapi import FastAPI

app = FastAPI(title="Math2Latex API")

@app.get("/health")
def health():
    return {"status": "ok"}
```

Bạn nên hiểu:

- `FastAPI` là framework xây dựng API
- `@app.get(...)` là route HTTP GET
- `/health` là route kiểm tra service có sống không

### Bước 5: Hiểu file frontend chính

File cần đọc trước:

- frontend/src/App.jsx

Nội dung mặc định ban đầu là giao diện demo của React + Vite. Bạn nên thay đổi phần này để làm giao diện của dự án Math2Latex.

---

## 4. Checklist hoàn thành tuần 1

### Backend
- [ ] Cài đặt Docker và Docker Compose
- [ ] Chạy được backend thành công
- [ ] Kiểm tra endpoint `/health`
- [ ] Hiểu FastAPI cơ bản

### Frontend
- [ ] Chạy được React app
- [ ] Truy cập giao diện trên port 5173
- [ ] Hiểu cấu trúc component React

### Database
- [ ] PostgreSQL chạy thành công
- [ ] Hiểu cách kết nối DB qua biến môi trường

### Tổng quan dự án
- [ ] Hiểu được mục tiêu của sản phẩm
- [ ] Hiểu vai trò của frontend, backend, database
- [ ] Lập kế hoạch cho tuần 2

---

## 5. Nhiệm vụ nên làm ngay

### Nhiệm vụ bắt buộc

1. Chạy Docker Compose và xác nhận tất cả service chạy
2. Kiểm tra backend `/health`
3. Truy cập frontend và xác nhận giao diện hiển thị
4. Đọc kỹ file backend/app/main.py
5. Đọc kỹ file frontend/src/App.jsx
6. Ghi chú lại cấu trúc dự án và các file quan trọng

### Nhiệm vụ nâng cao (nếu còn thời gian)

- Tạo một trang upload PDF đơn giản ở frontend
- Tạo một API upload file ở backend
- Thử gửi request POST đến backend
- Tạo mô tả chức năng của ứng dụng cho nhóm

---

## 6. Kết quả mong muốn cuối tuần 1

Đến cuối tuần 1, bạn cần có:

- Dự án chạy được ở local
- Backend có API kiểm tra trạng thái
- Frontend có thể mở được trên trình duyệt
- Hiểu rõ mục tiêu của dự án và kế hoạch phát triển
- Có sẵn nền tảng để tuần 2 thực hiện upload PDF và OCR

---

## 7. Gợi ý kế hoạch cho tuần 2

Tuần 2 nên tập trung vào:

- Upload file PDF hoặc ảnh lên backend
- Lưu file tạm thời hoặc vào thư mục upload
- Xử lý OCR / nhận diện công thức toán
- Trả kết quả dạng LaTeX

---

## 8. Lưu ý quan trọng

- Hãy chạy dự án bằng Docker để tránh lỗi môi trường
- Không nên bắt đầu viết logic phức tạp quá sớm
- Tập trung vào việc hiểu hệ thống trước khi làm chức năng lớn
- Nếu backend hoặc frontend báo lỗi, hãy kiểm tra log và port

---

## 9. Phải làm những gì trong tuần 1

Tuần 1 không phải là tuần làm chức năng chính của hệ thống, mà là tuần chuẩn bị nền móng để sau này làm nhanh và đúng hướng. Bạn cần làm theo thứ tự sau:

### 9.1. Làm quen với dự án

- Đọc kỹ file cấu hình Docker: `docker-compose.yml`
- Hiểu vai trò của 3 thành phần: backend, frontend, database
- Biết cách khởi động và tắt project bằng Docker
- Biết cách truy cập từng service trên port tương ứng

### 9.2. Chạy được dự án ở local

- Chạy Docker Compose để build project
- Kiểm tra frontend mở được trên `http://localhost:5173`
- Kiểm tra backend có thể trả về JSON health status
- Kiểm tra PostgreSQL có khởi động thành công và sẵn sàng nhận kết nối

Nếu 1 trong 3 thành phần không chạy, bạn chưa hoàn thành tuần 1.

### 9.3. Học cách đọc code dự án

Bạn phải đọc và hiểu tối thiểu các file sau:

- `backend/app/main.py` → hiểu cách tạo FastAPI app, route, response
- `backend/requirements.txt` → hiểu các thư viện backend cần có
- `docker-compose.yml` → hiểu service, port, biến môi trường, dependency
- `frontend/package.json` → hiểu script dev/build và dependencies
- `frontend/src/App.jsx` → hiểu React app được render như thế nào

### 9.4. Tạo thói quen làm việc đúng

- Mỗi khi chạy dự án, kiểm tra log của container
- Nếu có lỗi, đọc lỗi đầu tiên trước, không chạy nhiều lệnh ngẫu nhiên
- Học cách thay đổi code và reload tự động bằng Docker/Vite
- Ghi lại những bước đã làm để khi gặp lỗi có tham khảo lại

### 9.5. Chuẩn bị cho chức năng chính của dự án

Tuần 1 không cần làm xong OCR hay chuyển PDF sang LaTeX, nhưng bạn phải hiểu rõ rằng các chức năng này sẽ nằm ở đâu:

- Upload file sẽ ở frontend và backend
- Xử lý PDF/ảnh sẽ ở backend
- OCR / nhận dạng công thức toán sẽ ở service riêng trong backend
- Kết quả LaTeX sẽ trả về cho frontend hiển thị

---

## 10. Phải học những gì để làm được dự án

### 10.1. Học Python cơ bản

Bạn cần nắm rõ các kiến thức sau:

- Biến, kiểu dữ liệu, list, dict
- Function và return value
- Class và object cơ bản
- Import module
- Xử lý file và thư mục
- Làm việc với JSON

Vì backend làm bằng FastAPI nên bạn cần hiểu cách tạo API và xử lý dữ liệu đầu vào/đầu ra.

### 10.2. Học FastAPI cơ bản

Bạn nên biết:

- Cách tạo app FastAPI
- Cách định nghĩa route bằng `@app.get`, `@app.post`
- Cách nhận dữ liệu từ request
- Cách trả về JSON
- Cách xử lý file upload
- Cách bắt lỗi đơn giản

Bạn có thể tự học qua ví dụ nhỏ như:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
def hello():
    return {"message": "hello"}
```

### 10.3. Học JavaScript / React cơ bản

Bạn cần hiểu:

- JSX
- Component trong React
- State (`useState`)
- Event handler như `onClick`
- Render dữ liệu động
- Form và input

Ví dụ bạn cần biết cách làm form upload file, nút submit, và hiển thị kết quả.

### 10.4. Học Docker cơ bản

Bạn cần hiểu các khái niệm sau:

- Container là gì
- `docker compose up` dùng để khởi động nhiều service cùng lúc
- Port mapping
- Volume mount
- Container dependency

Đây là nền tảng để dự án của bạn chạy ổn trên máy khác.

### 10.5. Học PostgreSQL cơ bản

Hiện tại chưa cần làm truy vấn phức tạp, nhưng bạn nên biết:

- Database là nơi lưu dữ liệu
- Cấu trúc bảng
- Khái niệm `connection string`
- Cách kết nối từ backend
- Làm quen với SQL cơ bản: SELECT, INSERT, UPDATE

### 10.6. Học khái niệm OCR / PDF / LaTeX

Mặc dù tuần 1 chưa làm chức năng chính nhưng bạn nên có khái niệm ban đầu:

- PDF là file tài liệu có định dạng cố định
- OCR giúp chuyển chữ từ ảnh/PDF sang dạng text
- Công thức toán cần chuyển sang dạng LaTeX để hiển thị đúng
- Kết quả cuối cùng của sản phẩm là một phép chuyển từ hình ảnh/công thức toán sang mã LaTeX

---

## 11. Kỹ năng cần có sau khi kết thúc tuần 1

Sau khi hoàn thành tuần 1, bạn nên có thể:

- Khởi động được môi trường dự án bằng Docker
- Mở được frontend và backend trên localhost
- Biết đọc và sửa code trong FastAPI và React
- Hiểu cách API hoạt động
- Biết cách kiểm tra lỗi từ console và logs
- Có định hướng rõ cho các phần làm tiếp theo

---

## 12. Mức độ hoàn thành tốt

Một người hoàn thành tốt tuần 1 sẽ có các dấu hiệu sau:

- Không còn thấy lạ với FastAPI
- Không còn thấy lạ với JSX và React
- Có thể mô tả vai trò của từng file trong project
- Có thể khởi động project mà không cần ai hướng dẫn
- Biết dự án này sẽ làm gì ở tuần 2, tuần 3, tuần 4

---

## 13. Kết luận

Tuần 1 không cần làm quá nhiều chức năng phức tạp. Điều quan trọng là:

- hiểu bài toán
- chạy được dự án
- có nền tảng rõ ràng cho các tuần sau
- nắm được kiến thức tối thiểu cần học để làm tiếp theo

Nếu tuần 1 làm tốt, các tuần tiếp theo sẽ dễ triển khai hơn rất nhiều.
