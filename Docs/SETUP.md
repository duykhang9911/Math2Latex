# Cài đặt và chạy local

## Yêu cầu

- Docker Desktop với Linux containers/WSL 2.
- Git, PowerShell và Internet cho image/dependencies/model weights.
- NVIDIA driver nếu dùng GPU; host cần `nvidia-smi` chạy được.

## Khởi động

```powershell
docker compose config -q
docker compose up -d --build
docker compose ps
docker compose exec backend alembic upgrade head
```

Chờ `db` và `redis` healthy, `backend`, `worker`, `frontend` Up.

- Web: http://localhost:5173
- API health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

## GPU check

```powershell
nvidia-smi
docker compose exec worker nvidia-smi
docker compose exec worker python -c "import torch,onnxruntime; print(torch.cuda.is_available(), onnxruntime.get_available_providers())"
```

`nvidia-smi` thành công chưa chứng minh detector/recognizer chạy GPU. Chạy inference smoke test và kiểm tra worker log. Pix2Text ONNX CUDA từng báo cảnh báo plugin EP; nếu còn lỗi, đặt `MATH_DETECTOR_BACKEND=pytorch` cho worker và so sánh latency/quality trước khi chốt.

## Queue/logs

```powershell
docker compose exec redis redis-cli ping
docker compose exec redis redis-cli INFO persistence
docker compose exec backend rq info --url redis://redis:6379/0
docker compose logs --tail 100 backend worker redis
```

Redis dùng AOF và volume. `docker compose down` giữ data; `docker compose down -v` xóa cả PostgreSQL/Redis volumes, không chạy nếu cần giữ dữ liệu.

## File/model storage

Uploads ở `backend/uploads/<document_uuid>/`. Model cache hiện nằm trong filesystem container; cần cân nhắc volume cache riêng để tránh tải lại sau recreate. Production nhiều host cần shared object storage.

Compose hiện có local default credentials; không dùng ở môi trường chia sẻ/production. Chưa có authentication hoàn chỉnh, không expose API công khai.

## Troubleshooting

- Worker không nhận job: kiểm tra Redis healthy, `REDIS_URL`, queue name `math2latex`, worker logs.
- Bảng thiếu: chạy migration và kiểm tra `alembic current`.
- Font toán lỗi: DevTools Network, kiểm tra `/mathlive-fonts/*.woff2` trả 200.
- OCR chậm: kiểm tra provider, cold model download, page count và worker log.
- GPU: kiểm tra trong worker, không chỉ trên host.
- Đăng ký/đăng nhập không tạo cookie: kiểm tra `AUTH_SECRET` có độ dài tối thiểu 32 ký tự và origin frontend có trong CORS allowlist.

## Authentication configuration

Copy `.env.example` to `.env` and set `AUTH_SECRET` to a random value of at least 32 characters before using non-test data. `AUTH_COOKIE_SECURE=false` is for local HTTP only; set it to `true` behind HTTPS. Never commit `.env`.