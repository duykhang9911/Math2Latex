# Quy chuẩn đóng góp

## Code

- Giữ diff nhỏ, theo conventions hiện tại; không refactor unrelated.
- Router chỉ xử lý HTTP/validation/transaction/enqueue; service giữ logic; models là mapping; schemas là API contract.
- Không chạy Pix2Text/pix2tex lâu trong request handler.
- Bbox pixel, `latex_raw` bất biến, `latex_final` chỉ từ Submit.
- Alembic revision mới cho schema changes.
- Không thêm dependency model nặng nếu không có need/benchmark.

## Bảo mật và dữ liệu

- Không commit `.env`, credentials, PDF/crop cá nhân, model weights, database dumps.
- Không coi filename/MIME của browser là đủ để xác thực upload; cần server-side limits/content validation.
- CORS hiện phục vụ local development; không expose cấu hình rộng ra production.
- Auth chưa hoàn tất; không public hóa dữ liệu.

## Test/checklist review

- Backend: schema/status logic, API/DB integration, Redis unavailable/retry.
- Worker: restart, duplicate enqueue, job failure, OCR failure.
- Frontend: MathLive ↔ LaTeX, overlay pointer/keyboard, saved/unsaved/errors.
- Pipeline: nhiều trang, không công thức, malformed/encrypted PDF.
- GPU: provider và inference trong worker; không dùng `nvidia-smi` đơn lẻ làm bằng chứng.
- Chạy `docker compose config -q`, frontend build/lint, migration và checks phù hợp.
- Ghi rõ test nào không chạy được và vì sao.