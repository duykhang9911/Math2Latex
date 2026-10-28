# Ownership và hợp đồng

Dự án hiện là một ứng dụng nhỏ; phân ranh theo trách nhiệm kỹ thuật/workflow, không ép thành các micro-module độc lập.

| Phần | Owner đề xuất | Sở hữu | Không nên làm |
|---|---|---|---|
| API/document | Backend API | Route, validation HTTP, transaction, status response | Chạy inference lâu trong request |
| Identity/auth | Backend API/security | Register/login/logout/me, password hash, session cookie | Trả password hash/token trong JSON |
| Core | Backend platform | DB session, Redis/RQ config/helper | Nhét business OCR vào core |
| Formula data | Data/backend | Model, schema, migration, constraints | Sửa migration đã áp dụng |
| PDF processing | Processing | Render pages, bbox, crop, MFD | Ghi `latex_final` |
| OCR | Processing | Model lifecycle, raw OCR, failure/retry | Ghi đè raw bằng nội dung người dùng |
| Review UI | Frontend | Polling, pages, overlay, LaTeX/MathLive, Submit | Báo lưu thành công trước response |
| Platform/QA | DevOps/maintainer | Compose, Redis, worker, GPU, logs | Commit secret/model/upload |
| Docs/integration | Maintainer | SRS, diagrams, setup, backlog | Tự tạo thông tin cá nhân nhóm |

## Contract cố định

- Bbox là pixel của page image; `0 <= x_min < x_max <= width`, `0 <= y_min < y_max <= height`.
- Page number trong API/database bắt đầu từ 1.
- `latex_raw` là OCR; `latex_final` chỉ được ghi bởi Submit.
- `image_path` là server-side path, không nhận path tùy ý từ browser.
- Queue callable phải importable trong worker; job payload không chứa secret.
- API và worker cập nhật document/formula bằng transaction và trạng thái rõ.
- API xác định user từ signed cookie; không nhận `uploaded_by` từ request body.
- Document query phải lọc owner; UUID khó đoán không thay thế authorization.

## Review chéo

Schema/status/migration cần backend + DB review; bbox/API contract cần backend + frontend review; GPU provider và Docker cần processing + platform review; MathLive/Node/assets cần frontend + platform review.