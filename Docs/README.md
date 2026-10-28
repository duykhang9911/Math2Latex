# Tài liệu Math2Latex

Mỗi chủ đề có một nguồn chuẩn; tài liệu khác nên liên kết thay vì sao chép dài.

| Nhu cầu | Tài liệu |
|---|---|
| Tổng quan/chạy nhanh | [README](../README.md), [SETUP](SETUP.md) |
| Yêu cầu/nghiệm thu | [SRS](SRS.md) |
| Kiến trúc/luồng | [ARCHITECTURE](ARCHITECTURE.md) |
| Ownership | [MODULE_OWNERSHIP](MODULE_OWNERSHIP.md) |
| Vị trí code/test | [PROJECT_STRUCTURE_GUIDE](PROJECT_STRUCTURE_GUIDE.md) |
| Database/migration | [DATABASE](DATABASE.md) |
| Làm feature | [DEVELOPMENT_PLAYBOOK](DEVELOPMENT_PLAYBOOK.md) |
| Chất lượng/review | [CONTRIBUTING](CONTRIBUTING.md) |
| Branch/commit/PR | [GIT_WORKFLOW](GIT_WORKFLOW.md) |
| Thành viên/vai trò | [TEAM](TEAM.md) |
| Backlog/phân công | [PHAN_CONG_CONG_VIEC](PHAN_CONG_CONG_VIEC.md) |
| Backend | [BACKEND_GUIDE](modules/BACKEND_GUIDE.md) |
| Frontend | [FRONTEND_GUIDE](modules/FRONTEND_GUIDE.md) |

## Nguồn sự thật

- Behavior đang chạy: source và tests hiện tại.
- Requirement đã thống nhất: `SRS.md`.
- Schema: model + Alembic revisions; `DATABASE.md` giải thích.
- Cấu hình thật: `docker-compose.yml`, Dockerfiles và environment.
- Thành viên: `TEAM.md`; không tự điền tên/MSSV chưa được xác nhận.

Khi docs và code khác nhau, ghi lại khác biệt; không giả định tài liệu cũ đúng hơn code.