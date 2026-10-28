# Hướng dẫn làm việc trong repository

Đọc theo thứ tự: `README.md`, `Docs/SRS.md`, `Docs/ARCHITECTURE.md`, `Docs/MODULE_OWNERSHIP.md`, `Docs/PROJECT_STRUCTURE_GUIDE.md`, `Docs/DEVELOPMENT_PLAYBOOK.md`, rồi source/test của phần liên quan. Xem `Docs/PHAN_CONG_CONG_VIEC.md` khi nhận task hoặc tích hợp.

## Quy tắc

- Giữ backend và frontend tách theo ownership hiện tại; không tạo module nghiệp vụ giả khi chưa cần.
- API validate HTTP và enqueue job; không chạy MFD/pix2tex lâu trong request handler.
- Worker callable phải import được trong process RQ; job nhận UUID/path nội bộ, không nhận secret từ client.
- PostgreSQL là nguồn sự thật cho document/formula; Redis/RQ chỉ điều phối job.
- Giữ `latex_raw` nguyên bản; Submit chỉ cập nhật `latex_final`.
- Bbox dùng pixel của page image. Validate bounds phía backend.
- Không sửa Alembic revision đã áp dụng; thêm migration mới.
- Không commit upload PDF/crop, model weights, secrets, `.venv`, `node_modules`, `dist`.
- Không tuyên bố GPU hoạt động chỉ từ `nvidia-smi`; kiểm tra PyTorch/ONNX provider và inference trong worker.
- Không xóa/ghi đè thay đổi người dùng ngoài phạm vi.

## Quy trình task

1. Xác định requirement, actor, API/data contract, status transition và phạm vi file.
2. Nêu giả thuyết kiểm chứng được; chạy check nhỏ nhất.
3. Thực hiện vertical slice nhỏ, cập nhật docs nguồn khi contract/config thay đổi.
4. Chạy test/build/lint liên quan; ghi rõ validation chưa chạy được.
5. Báo file sửa, bằng chứng, giới hạn và việc còn lại.

## Lệnh thường dùng

```powershell
docker compose config -q
docker compose ps
docker compose logs --tail 100 backend worker redis
docker compose exec backend alembic upgrade head
Push-Location frontend; npm run build; npm run lint; Pop-Location
```