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

Compose hiện có local default database credentials; không dùng ở môi trường chia sẻ/production. Đăng ký/đăng nhập username và mật khẩu đã có; mỗi document mới được gắn với user đăng nhập. Email verification, password reset, roles và login rate limiting chưa triển khai; không expose app công khai trước khi giải quyết các yêu cầu này.

## Xem database bằng pgAdmin 4

pgAdmin không tự tìm database trong Docker; cần đăng ký server một lần. Chuột phải **Servers** → **Register** → **Server…**, đặt `Name` ở tab General, rồi điền tab Connection theo `docker-compose.yml`:

| Trường | Giá trị |
|---|---|
| Host name/address | `127.0.0.1` |
| Port | `5432` |
| Maintenance database | `math2latex` |
| Username / Password | `math2latex_user` / `math2latex_pass` |

Bảng nằm ở **Servers → Math2Latex → Databases → math2latex → Schemas → public → Tables**: `users`, `documents`, `formula_entries`, `logs`, `alembic_version`. Dùng `127.0.0.1` thay vì `localhost` vì cổng 5432 trên Windows có thể bị `wslrelay` giữ ở địa chỉ IPv6. Credentials này chỉ dành cho local. Cần `db` đang chạy (`docker compose ps`).

Không có pgAdmin thì dùng `docker compose exec db psql -U math2latex_user -d math2latex -c "\dt"`.

## Phát triển và test

- Backend/worker mount `./backend` vào container. `rq worker` không tự nạp lại code, và `uvicorn --reload` đã không nhận ra file đổi trên Windows bind mount khi kiểm thử. Sau khi sửa code backend, chạy `docker compose restart backend worker`.
- Chạy test backend (pytest chưa có sẵn trong image; lệnh `pip install` chỉ ảnh hưởng container đang chạy): xem `backend/tests/README.md`.
- Dọn thư mục upload mồ côi: `docker compose exec backend python -m app.services.retention` (dry-run; chính sách ở [DATABASE](DATABASE.md)).
- Giới hạn upload, timeout, giới hạn đăng nhập sai và `CORS_ORIGINS` đổi bằng biến môi trường (bảng ở [ARCHITECTURE](ARCHITECTURE.md)); đặt trong `.env` cạnh `docker-compose.yml` rồi `docker compose up -d`.

## Troubleshooting

- Worker không nhận job: kiểm tra Redis healthy, `REDIS_URL`, queue name `math2latex`, worker logs.
- Bảng thiếu: chạy migration và kiểm tra `alembic current`.
- Font toán lỗi: DevTools Network, kiểm tra `/mathlive-fonts/*.woff2` trả 200.
- OCR chậm: kiểm tra provider, cold model download, page count và worker log.
- GPU: kiểm tra trong worker, không chỉ trên host.
- Đăng ký/đăng nhập không tạo cookie: kiểm tra `AUTH_SECRET` có độ dài tối thiểu 32 ký tự và origin frontend có trong `CORS_ORIGINS`.
- 429 khi đăng nhập: đăng nhập sai quá nhiều lần; chờ hết `Retry-After` hoặc xóa khóa `login-fail:*` trong Redis (chỉ khi chắc chắn là lần thử của chính bạn).
- 403 "Origin không được phép" khi gọi API từ trình duyệt: origin của frontend chưa có trong `CORS_ORIGINS`.
- Upload bị từ chối: 400 (không phải PDF hợp lệ/cần mật khẩu), 413 (quá lớn), 422 (quá nhiều trang hoặc trang quá lớn).

## Authentication configuration

Copy `.env.example` to `.env` and set `AUTH_SECRET` to a random value of at least 32 characters before using non-test data. `AUTH_COOKIE_SECURE=false` is for local HTTP only; set it to `true` behind HTTPS. Never commit `.env`.