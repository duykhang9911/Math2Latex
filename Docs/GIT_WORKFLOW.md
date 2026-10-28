# Git workflow

## Branch và commit

- Branch theo phạm vi: `feature/region-keyboard`, `fix/ocr-retry`, `docs/project-guide`.
- Commit ngắn, mô tả thay đổi: `Add RQ worker queue`, `Document formula pipeline`.
- Không commit uploads, model cache/weights, `.venv`, `node_modules`, `dist`, generated MathLive fonts hoặc secrets.

## Pull request

Mỗi PR ghi: task/FR, thay đổi backend/frontend/schema/ops, migration, test thực sự đã chạy, ảnh/clip UI nếu đổi UX, rủi ro và blocker.

## Trước khi gửi

```powershell
git status --short
git diff --check
docker compose config -q
Push-Location frontend; npm run build; npm run lint; Pop-Location
```

Không force-push nhánh dùng chung nếu chưa thống nhất với nhóm.