# Math2Latex

Math2Latex là ứng dụng web chuyển công thức trong PDF thành LaTeX có thể chỉnh sửa. Hệ thống render PDF, đề xuất vùng công thức, chạy OCR khi người dùng xác nhận, rồi lưu riêng kết quả máy và kết quả đã duyệt.

## Pipeline

```text
Upload PDF -> render trang -> detect vùng -> người dùng rà vùng
           -> OCR -> sửa bằng LaTeX/MathLive -> Submit
```

`latex_raw` giữ kết quả OCR ban đầu; `latex_final` là nội dung người dùng gửi.

## Công nghệ

- Frontend: React, Vite, MathLive
- Backend/API: Python, FastAPI, SQLAlchemy
- Database: PostgreSQL + Alembic
- Background jobs: Redis + RQ
- PDF: PyMuPDF; detection: Pix2Text MFD; recognition: pix2tex
- Local development: Docker Compose

## Chạy local

Cần Docker Desktop dùng Linux containers. GPU là tùy chọn; CUDA cần được xác minh trong worker.

```powershell
docker compose config -q
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose ps
```

- Web: http://localhost:5173
- API health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

Hướng dẫn chi tiết: [Docs/SETUP.md](Docs/SETUP.md). Hướng dẫn học dự án: [doc.md](doc.md).

## Bắt đầu

- [AGENTS.md](AGENTS.md): quy tắc làm việc trong repository
- [Docs/README.md](Docs/README.md): mục lục tài liệu
- [Docs/SRS.md](Docs/SRS.md): yêu cầu và tiêu chí nghiệm thu
- [Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md): kiến trúc và luồng dữ liệu
- [Docs/PROJECT_STRUCTURE_GUIDE.md](Docs/PROJECT_STRUCTURE_GUIDE.md): vị trí source/test
- [Docs/PHAN_CONG_CONG_VIEC.md](Docs/PHAN_CONG_CONG_VIEC.md): backlog và phân công đề xuất

OCR có thể nhận sai; kết quả cần người dùng rà trước khi Submit. Pipeline đã xác minh cho PDF; upload ảnh riêng chưa được nghiệm thu.