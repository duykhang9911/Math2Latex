# Tuần 2 - Math2Latex

## 1. Mục tiêu

Tuần 2 tập trung vào việc xây dựng chức năng upload file đầu tiên của hệ thống. Mục tiêu là cho phép người dùng upload ảnh hoặc PDF chứa công thức toán từ frontend lên backend, backend lưu file vào thư mục `uploads`, và trả về thông tin file đã upload.

---

## 2. Các bước đã thực hiện

### Bước 1: Tạo thư mục lưu file

Tôi tạo thư mục lưu trữ file upload ở backend:

```text
backend/uploads/
```

Mục đích của thư mục này là lưu các file người dùng upload lên server để xử lý ở các tuần tiếp theo.

---

### Bước 2: Viết API upload trong FastAPI

Trong file [backend/app/main.py](backend/app/main.py), tôi bổ sung route:

```python
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        return {"status": "error", "message": "No file selected"}

    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_exts:
        return {
            "status": "error",
            "message": f"Unsupported file type: {file_ext}. Allowed: {sorted(allowed_exts)}",
        }

    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "size": len(content),
        "path": str(save_path),
    }
```

Điều này cho phép backend:

- nhận file từ client
- kiểm tra tên file và định dạng
- lưu file vào thư mục uploads
- trả lại thông tin file đã upload

---

### Bước 3: Cấu hình CORS để frontend có thể gọi API

Tôi thêm middleware CORS cho backend để frontend ở localhost:5173 có thể gửi request lên localhost:8000 mà không bị chặn bởi browser.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Điều này rất cần thiết vì frontend và backend chạy trên hai port khác nhau trong môi trường dev.

---

### Bước 4: Thay giao diện demo React bằng giao diện upload file

Trong file [frontend/src/App.jsx](frontend/src/App.jsx), tôi thay giao diện mặc định của Vite bằng một form upload đơn giản:

- chọn file
- hiển thị tên file
- nút upload
- gọi API backend
- hiển thị trạng thái upload
- hiển thị thông tin file trả về

Code chính gồm:

```jsx
const handleUpload = async () => {
  const formData = new FormData()
  formData.append('file', selectedFile)

  const response = await fetch('http://localhost:8000/upload', {
    method: 'POST',
    body: formData,
  })

  const data = await response.json()
  setFileInfo(data)
  setStatus('Upload thành công!')
}
```

---

### Bước 5: Viết CSS cho giao diện upload

Trong file [frontend/src/App.css](frontend/src/App.css), tôi viết lại style để giao diện đẹp hơn và phù hợp với mục tiêu của dự án.

Việc này giúp:

- card upload rõ ràng
- nút upload dễ nhìn
- thông báo trạng thái dễ hiểu
- giao diện thân thiện với người dùng

---

## 3. Kết quả kiểm tra thực tế

Sau khi sửa xong, tôi tiến hành kiểm tra bằng cách:

1. chạy lại Docker Compose
2. mở frontend trên localhost:5173
3. chọn một file mẫu
4. gửi upload lên backend
5. kiểm tra phản hồi từ API

Kết quả thực tế đã xác nhận rằng:

- backend có route `/upload`
- frontend có thể gửi file lên backend
- file được lưu vào thư mục backend/uploads
- API trả về dữ liệu JSON với tên file, kích thước và đường dẫn

---

## 4. Kết luận tuần 2

Tuần 2 đã hoàn thành phần upload file cơ bản. Đây là bước quan trọng vì đây là nền tảng cho các chức năng lớn hơn của dự án như:

- OCR
- xử lý ảnh/PDF
- trích xuất công thức toán
- chuyển đổi sang LaTeX

Sau khi upload file thành công, chúng ta sẽ sang tuần 3 để xử lý nội dung file và nhận diện công thức toán.

---

## 5. Tài liệu liên quan

- [backend/app/main.py](backend/app/main.py)
- [frontend/src/App.jsx](frontend/src/App.jsx)
- [frontend/src/App.css](frontend/src/App.css)
- [tuan2.md](tuan2.md)
