# Tuần 2 - Math2Latex

## Mục tiêu tuần 2

Tuần 2 tập trung vào việc phát triển chức năng cốt lõi đầu tiên của dự án: upload file và xử lý file đầu vào. Mục tiêu chính là:

- Tạo giao diện upload file trên frontend
- Xây dựng API upload file trên backend
- Lưu file vào thư mục `uploads`
- Kiểm tra dữ liệu đầu vào và chuẩn bị cho OCR và chuyển đổi LaTeX
- Chuẩn bị nền tảng cho tuần 3 và tuần 4

---

## 1. Hiểu mục tiêu của tuần 2

Sau khi đã hoàn thành tuần 1, dự án đã chạy được ở local. Tuần 2 sẽ chuyển sang phần có tính nghiệp vụ rõ hơn:

- Người dùng sẽ upload ảnh hoặc PDF chứa công thức toán
- Backend sẽ nhận file và lưu trên server
- Frontend sẽ hiển thị trạng thái upload thành công hoặc thất bại
- Sau đó, dự án sẽ tiếp tục xử lý OCR và chuyển đổi thành LaTeX ở các tuần sau

---

## 2. Công việc cần làm trong tuần 2

### Bước 1: Tạo giao diện upload ở frontend

Bạn cần chỉnh sửa file frontend để có:

- một ô upload file
- một nút "Chọn file"
- một nút "Upload"
- vùng hiển thị tên file đã chọn
- trạng thái loading hoặc thành công

Ví dụ giao diện cơ bản cần có:

- tiêu đề: "Upload tài liệu toán học"
- input type file
- button upload
- xem trước tên file

### Bước 2: Tạo API upload ở backend

Backend cần có route để nhận file từ frontend. Ví dụ:

```python
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    return {"filename": file.filename}
```

Mục tiêu của API:

- nhận file từ client
- kiểm tra loại file hợp lệ
- lưu vào thư mục `uploads`
- trả về thông tin file đã upload

### Bước 3: Lưu file vào thư mục uploads

Bạn cần tạo thư mục:

```text
backend/uploads/
```

Tại đây, tất cả file upload sẽ được lưu. Cần đảm bảo:

- thư mục tồn tại
- backend có quyền ghi file
- không bị lỗi khi upload

### Bước 4: Kiểm tra dữ liệu đầu vào

Trước khi xử lý ngoài nghiệp vụ, cần kiểm tra:

- file có rỗng không
- định dạng file có hợp lệ không
- kích thước file có quá lớn không
- file có phải PDF/ảnh không

### Bước 5: Chuẩn bị cho OCR và chuyển đổi LaTeX

Mục tiêu của tuần 2 không phải là làm xong OCR ngay, nhưng cần chuẩn bị tốt để tuần 3, tuần 4 thực hiện được. Cần hiểu:

- file upload sẽ được xử lý như dữ liệu đầu vào cho OCR
- mỗi file cần có metadata: tên, kích thước, đường dẫn lưu trữ
- sau khi upload, backend sẽ có thể tiếp tục gọi mô hình xử lý ở bước sau

---

## 3. Cấu trúc dự án cần phát triển thêm

### Backend

- `backend/app/api` → nơi tạo route API upload
- `backend/app/services` → nơi xử lý upload, file và OCR tương lai
- `backend/uploads` → thư mục chứa file người dùng upload

### Frontend

- `frontend/src/App.jsx` → giao diện chính
- có thể thêm component upload form
- có thể xử lý `onChange` với file input

---

## 4. Checklist hoàn thành tuần 2

### Backend
- [ ] Tạo endpoint upload file
- [ ] Lưu file vào thư mục `uploads`
- [ ] Kiểm tra file hợp lệ
- [ ] Trả về thông báo upload thành công

### Frontend
- [ ] Tạo form upload
- [ ] Chọn file thành công
- [ ] Gửi file lên backend
- [ ] Hiển thị trạng thái upload

### Tổng quan
- [ ] Frontend và backend giao tiếp được
- [ ] File upload được lưu đúng vị trí
- [ ] Dự án sẵn sàng cho OCR và chuyển đổi LaTeX

---

## 5. Nhiệm vụ cần làm ngay

### Nhiệm vụ bắt buộc

1. Tạo thư mục `backend/uploads`
2. Viết API upload file trong FastAPI
3. Chỉnh sửa frontend để có form upload
4. Kiểm tra dữ liệu gửi lên backend
5. Xác nhận file đã lưu được trên server

### Nhiệm vụ nâng cao (nếu còn thời gian)

- Thêm validation loại file
- Hiển thị tên file trên giao diện
- Hiển thị trạng thái upload loading
- Chuyển dữ liệu file sang định dạng JSON hoặc response rõ ràng

---

## 6. Kỹ năng cần học trong tuần 2

### 6.1. Python

- xử lý file upload trong FastAPI
- làm việc với `UploadFile`
- tạo thư mục và lưu file vào disk
- xử lý exception đơn giản

### 6.2. FastAPI

- `@app.post()`
- `File(...)`
- `UploadFile`
- response JSON

### 6.3. React

- `input type="file"`
- `FormData`
- `fetch` hoặc `axios`
- xử lý loading và lỗi

### 6.4. HTTP

- cách gửi file từ frontend lên backend
- cách đọc response từ API
- cách debug request và lỗi 400, 500

---

## 7. Ví dụ cơ bản upload file

### Backend

```python
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from pathlib import Path

app = FastAPI(title="Math2Latex API")
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    save_path = UPLOAD_DIR / file.filename
    with save_path.open("wb") as f:
        f.write(await file.read())

    return {"filename": file.filename, "status": "uploaded"}
```

### Frontend

```jsx
const handleUpload = async () => {
  const formData = new FormData()
  formData.append('file', selectedFile)

  const response = await fetch('http://localhost:8000/upload', {
    method: 'POST',
    body: formData,
  })

  const data = await response.json()
  console.log(data)
}
```

---

## 8. Kết quả mong muốn cuối tuần 2

Đến cuối tuần 2, bạn cần có:

- frontend có form upload file hoạt động
- backend nhận file upload thành công
- file được lưu trong thư mục `uploads`
- hệ thống sẵn sàng cho tuần 3 xử lý OCR và chuyển đổi biểu thức toán

---

## 9. Kế hoạch cho tuần 3

Tuần 3 nên tập trung vào:

- OCR/nhận diện văn bản và công thức toán từ ảnh hoặc PDF
- Tạo service xử lý file ở backend
- Chuyển dữ liệu đầu vào sang định dạng dễ xử lý
- Tối ưu flow upload → preprocess → OCR → trả kết quả

---

## 10. Lưu ý quan trọng

- Không tải file quá lớn trong giai đoạn đầu
- Nên bắt đầu với file ảnh đơn giản trước khi làm PDF
- Luôn kiểm tra log backend khi upload không thành công
- Học cách debug bằng response và console

---

## 11. Kết luận

Tuần 2 là tuần đầu tiên bắt đầu làm chức năng chính của dự án. Đây là giai đoạn quan trọng vì từ đây bạn bắt đầu biến project từ “môi trường chạy được” thành “hệ thống có thể xử lý dữ liệu thật”.

Nếu tuần 2 làm tốt, tuần 3 và tuần 4 sẽ dễ dàng hơn rất nhiều vì bạn đã có sẵn cơ sở upload file và lưu trữ dữ liệu.
