# Hướng dẫn cấu trúc và vị trí đặt code

## Cây hiện tại + phần tài liệu mới

```text
Math2Latex/
|-- AGENTS.md
|-- README.md
|-- doc.md                         # hướng dẫn onboarding dài hiện có
|-- docker-compose.yml
|-- Docs/                          # tài liệu nghiệp vụ/kỹ thuật/nhóm
|   |-- README.md
|   |-- SRS.md
|   |-- ARCHITECTURE.md
|   |-- MODULE_OWNERSHIP.md
|   |-- PROJECT_STRUCTURE_GUIDE.md
|   |-- DATABASE.md
|   |-- SETUP.md
|   |-- DEVELOPMENT_PLAYBOOK.md
|   |-- CONTRIBUTING.md
|   |-- GIT_WORKFLOW.md
|   |-- TEAM.md
|   |-- PHAN_CONG_CONG_VIEC.md
|   `-- modules/
|       |-- BACKEND_GUIDE.md
|       `-- FRONTEND_GUIDE.md
|-- backend/
|   |-- Dockerfile, .dockerignore, requirements.txt, alembic.ini
|   |-- alembic/versions/
|   `-- app/{api,core,models,schemas,services}/
|-- frontend/
|   |-- Dockerfile, package.json, package-lock.json, scripts/
|   |-- public/                    # static assets, fonts sinh tự động
|   `-- src/{main.jsx,App.jsx,App.css,index.css,assets}/
`-- backend/uploads/               # runtime data; không commit
```

Không chia source thành các module nghiệp vụ giả khi ứng dụng hiện chỉ có một luồng document/formula. Thêm abstraction khi có use case/ownership độc lập.

## Backend: chọn vị trí

| Nhu cầu | Vị trí |
|---|---|
| FastAPI router/HTTP validation | `backend/app/api/` |
| DB session, queue, password/token security | `backend/app/core/` |
| SQLAlchemy tables | `backend/app/models/` |
| Request/response Pydantic | `backend/app/schemas/` |
| Auth endpoints | `backend/app/api/auth.py` |
| Render/detect/crop/OCR use case | `backend/app/services/` |
| Schema change | `backend/alembic/versions/`, revision mới |
| Unit/API/worker tests đề xuất | `backend/tests/unit/`, `api/`, `worker/` |

API không chạy inference trong request handler. Router validate/commit/enqueue; worker nhận callable và tham số serialize được.

## Frontend: chọn vị trí

| Nhu cầu | Vị trí |
|---|---|
| React bootstrap | `frontend/src/main.jsx` |
| Workflow state hiện tại | `frontend/src/App.jsx` |
| Component dùng lại (khi tách) | `frontend/src/components/` |
| API client (khi nhiều route) | `frontend/src/api/` |
| Styles | `frontend/src/` hoặc thư mục component |
| Bundled assets | `frontend/src/assets/` |
| URL static | `frontend/public/` |
| MathLive font copy | `frontend/scripts/copy-mathlive-fonts.mjs` -> `public/mathlive-fonts/` |
| UI tests đề xuất | `frontend/tests/` hoặc `src/__tests__/` |

`node_modules`, `dist`, generated fonts, uploads và model weights không commit.

## Test layout đề xuất

Hiện chưa có suite test chính thức. Khi bổ sung, đặt unit test gần logic; integration test cho API/DB/Redis; evaluation manifest cho PDF có quyền dùng. Không ghi các thư mục đề xuất thành tests đã tồn tại.