# Kịch bản demo và nội dung slides — Math2Latex (S6-04)

## Slides (đề xuất 12–15 slides)

### Slide 1: Trang bìa
- **Đề tài:** Math2Latex — Chuyển đổi công thức toán trong PDF sang LaTeX có thể chỉnh sửa
- Tên thành viên: Đoàn Trương Duy Khang, Ngô Hồ Tấn Toàn
- Giảng viên hướng dẫn: *(bổ sung)*
- Năm: 2026

### Slide 2: Bối cảnh và vấn đề
- Tài liệu toán PDF phổ biến trong giáo dục
- Công thức toán trong PDF không thể copy/chỉnh sửa
- Giáo viên/sinh viên cần chuyển sang LaTeX thủ công → mất thời gian
- **Mục tiêu:** Tự động phát hiện và nhận dạng công thức, cho phép chỉnh sửa trực quan

### Slide 3: Yêu cầu chức năng
- FR0: Đăng ký / Đăng nhập (Argon2 + JWT cookie)
- FR1: Upload PDF → Detect vùng → OCR sang LaTeX
- FR2: Sửa LaTeX ↔ MathLive hai chiều
- FR3: Submit lưu `latex_final`, giữ nguyên `latex_raw`
- FR4: Lịch sử tải lên, tải PDF gốc, xuất `.tex`

### Slide 4: Kiến trúc hệ thống
```
┌─ Browser ─┐   ┌── Backend ──┐   ┌── Worker ──┐
│  React    │──▶│  FastAPI    │──▶│  RQ + MFD  │
│  Vite     │   │  SQLAlchemy │   │  pix2tex   │
│  MathLive │   │  PostgreSQL │   │  ONNX CPU  │
└───────────┘   └─────────────┘   └────────────┘
                      │                  │
                   ┌──▼──┐          ┌────▼───┐
                   │ DB  │          │ Redis  │
                   └─────┘          └────────┘
```
- 5 services Docker Compose
- Background job queue (Redis + RQ)
- PostgreSQL là nguồn sự thật

### Slide 5: Công nghệ
| Layer | Công nghệ |
|---|---|
| Frontend | React 19, Vite 8, MathLive, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Alembic, Argon2 |
| AI/ML | Pix2Text MFD (detect), pix2tex (OCR), ONNX Runtime |
| Infra | Docker Compose, PostgreSQL, Redis + RQ |

### Slide 6: Luồng xử lý chính
1. User upload PDF
2. Backend tách trang (PyMuPDF)
3. Worker detect vùng công thức (Pix2Text MFD)
4. User xác nhận/sửa vùng (drag, keyboard)
5. Worker OCR crop → `latex_raw` (pix2tex)
6. User review + sửa bằng MathLive → Submit → `latex_final`
7. Export `.tex`

### Slide 7: Giao diện (screenshots)
- Trang đăng nhập
- Upload PDF + preview trang
- Overlay vùng công thức (drag/resize)
- FormulaEditor: LaTeX textarea + MathLive + Submit
- Lịch sử tải lên

### Slide 8: Kiểm thử
| Loại | Số test | Công cụ |
|---|---|---|
| Backend unit/API | 182+ | pytest, SQLite/PostgreSQL |
| Frontend component | 60 | Vitest, jsdom, Testing Library |
| Worker job | 10+ | pytest, fake model |
| **Tổng** | **242+** | |
- 100% FR có test tự động (17/17)
- 71% NFR có test (5/7)

### Slide 9: Đánh giá chất lượng
- Detector: Pix2Text MFD trên CPU, ~2s/trang
- OCR: pix2tex, cold ~8s, warm <1s/công thức
- Accuracy: *(bổ sung khi có submitted data)*
- Hạn chế: công thức phức tạp (ma trận lớn, dấu trên chữ) OCR có thể sai

### Slide 10: Bảo mật
- Argon2id hash mật khẩu
- JWT HttpOnly cookie (không LocalStorage)
- Rate limit 5 lần/15 phút (Redis counter)
- Owner scoping (chỉ thấy document của mình)
- Upload validation (size, type, filename sanitize)

### Slide 11: Kết quả đạt được
- ✅ Hệ thống hoạt động end-to-end trên Docker Compose
- ✅ 4 chức năng chính (FR0–FR4) đầy đủ
- ✅ 242+ test tự động
- ✅ Tài liệu kỹ thuật đầy đủ (SRS, ARCHITECTURE, SETUP, PLAYBOOK)
- ✅ Ma trận truy vết 100% FR

### Slide 12: Hạn chế và hướng phát triển
**Hạn chế:**
- Chỉ chạy CPU (chưa test GPU)
- Dữ liệu đánh giá ít (3–4 file)
- Chưa hỗ trợ inline math riêng lẻ
- MathLive không parse được một số ký hiệu LaTeX nâng cao

**Hướng phát triển:**
- Thêm GPU support cho tốc độ
- Batch processing nhiều PDF
- Collaborative editing
- Tích hợp LLM cho post-correction

### Slide 13: Q&A
- Cảm ơn!

---

## Kịch bản demo (5–7 phút)

### Bước 1: Khởi động (30s)
```bash
docker compose up -d
# Chờ healthy, mở http://localhost:5173
```

### Bước 2: Đăng ký + Đăng nhập (30s)
- Tạo tài khoản `demo` / `Demo@2026`
- Đăng nhập thành công → workspace

### Bước 3: Upload PDF (1 phút)
- Chọn file `2017-MathMethods1.pdf` (hoặc file được phép dùng)
- Click "Tải PDF" → thấy trạng thái "Đang tách trang"
- Đợi polling → "Đang tìm công thức" → "Chờ xác nhận vùng"

### Bước 4: Review vùng công thức (1 phút)
- Scroll qua các trang, thấy bbox đỏ trên ảnh
- **Demo drag:** kéo vùng sang vị trí đúng hơn
- **Demo resize:** kéo handle góc để thu/phóng
- **Demo keyboard:** dùng Arrow keys di chuyển, Shift+Arrow 10px, Alt+Arrow resize
- **Demo thêm vùng:** nhập tọa độ thủ công → "+ Thêm vùng"

### Bước 5: Chạy OCR (1 phút)
- Click "Xác nhận vùng & chạy OCR"
- Trạng thái chuyển "Đang nhận dạng LaTeX"
- Đợi polling → "OCR hoàn tất"

### Bước 6: Chỉnh sửa LaTeX (1.5 phút)
- Click vào công thức → thấy crop, textarea LaTeX, MathLive
- **Demo sync:** sửa LaTeX trong textarea → MathLive cập nhật
- **Demo MathLive:** sửa trong MathLive → textarea cập nhật
- Thử nhập công thức phức: `\frac{\partial f}{\partial x}`
- Click "Submit" → "Đã lưu"

### Bước 7: Lịch sử + Export (30s)
- Scroll lên thấy lịch sử tải lên
- Click "Tải PDF" → download PDF gốc
- Click "Xuất .tex" → download file `.tex` chứa `latex_final`

### Bước 8: Xử lý lỗi (30s, tuỳ chọn)
- Demo upload file không phải PDF → thông báo lỗi
- Demo session hết hạn → auto logout với message
- Demo rate limit → "Bạn đã gửi quá nhiều yêu cầu"

### Bước 9: Đăng xuất (10s)
- Click "Đăng xuất" → về trang login
