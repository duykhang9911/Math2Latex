# Math2Latex - Tài liệu học và hướng dẫn dự án

Tài liệu này dành cho thành viên mới của nhóm. Đọc theo thứ tự từ mục tiêu, luồng hoạt động, database, cấu trúc file rồi đến cách chạy ứng dụng. Mã nguồn mới nhất là nguồn sự thật khi thông tin trong các ghi chú tuần cũ không còn khớp.

---

## 1. Math2Latex là gì?

Math2Latex là ứng dụng web hỗ trợ chuyển công thức toán trong PDF thành LaTeX có thể chỉnh sửa.

Người dùng tải PDF lên. Hệ thống tách PDF thành ảnh từng trang, tự tìm các vùng có công thức, rồi nhận dạng vùng đó thành LaTeX. Người dùng kiểm tra vùng phát hiện, sửa kết quả bằng ô văn bản hoặc MathLive, sau đó lưu bản đã xác nhận.

Mục tiêu không phải là tin OCR tuyệt đối. Hệ thống giữ nguyên kết quả máy trong `latex_raw`, còn nội dung người dùng chấp nhận được lưu riêng trong `latex_final`. Nhờ vậy có thể sửa công thức mà không mất kết quả OCR gốc, đồng thời có dữ liệu để đo chất lượng nhận dạng sau này.

### Mục tiêu theo cách dễ nhớ

- Tìm công thức trong từng trang PDF.
- Chuyển vùng công thức thành LaTeX.
- Cho người dùng rà, sửa và xem trước biểu thức.
- Lưu kết quả đã sửa nhưng không xóa kết quả OCR ban đầu.

### Công nghệ chính

- Backend: Python, FastAPI, SQLAlchemy và Alembic.
- Database: PostgreSQL.
- Job nền: RQ và Redis.
- Xử lý PDF: PyMuPDF.
- Phát hiện vùng công thức: Pix2Text MFD.
- Nhận dạng công thức: pix2tex.
- Frontend: React, Vite và MathLive.
- Chạy local: Docker Compose.

> Hiện endpoint upload chấp nhận PDF, PNG, JPG và JPEG, nhưng pipeline render, detect và OCR được xác minh cho PDF. Không nên gọi luồng xử lý ảnh đơn lẻ là đã hoàn tất nếu chưa có kiểm thử riêng.

---

## 2. Toàn cảnh: một yêu cầu đi qua đâu?

```text
Trình duyệt (React)
       |
       | 1. Upload PDF / xem trang / sửa LaTeX
       v
FastAPI (backend)
       |                      \
       | ghi metadata           \ đưa công việc vào hàng đợi
       v                        v
PostgreSQL                  Redis + RQ
                                  |
                                  v
                            Worker nền
                    PyMuPDF -> Pix2Text MFD
                                  |
                    phát hiện bbox và tạo ảnh crop
                                  |
                    người dùng xác nhận vùng
                                  |
                              pix2tex
                                  |
                   latex_raw -> MathLive/textarea
                                  |
                      người dùng Submit
                                  |
                             latex_final
```

Ba loại dữ liệu được để ở đúng nơi:

1. **PostgreSQL** lưu thông tin cần tra cứu: tài liệu nào được tải lên, trạng thái hiện tại, công thức thuộc trang nào, tọa độ vùng và hai phiên bản LaTeX.
2. **Thư mục `backend/uploads/`** lưu các file lớn: PDF gốc, ảnh trang và ảnh crop. Database chỉ lưu đường dẫn đến các file này, không nhét ảnh vào từng dòng bảng.
3. **Redis/RQ** lưu công việc đang chờ worker xử lý. Redis không thay PostgreSQL và không phải nơi lưu kết quả LaTeX chính thức.

### Trình tự một PDF

1. Frontend gửi PDF tới `POST /api/documents/upload`.
2. Backend kiểm tra phần mở rộng, tạo UUID, lưu file nguồn và tạo một dòng `documents` trong PostgreSQL.
3. Backend đưa job render/detect vào Redis/RQ rồi trả `document_id` cho frontend. Request upload không phải chờ OCR xong.
4. Worker dùng PyMuPDF tạo các ảnh trang, rồi Pix2Text MFD tìm vùng công thức.
5. Mỗi vùng được lưu thành một dòng `formula_entries` với bbox, confidence, crop và trạng thái `proposed`.
6. Frontend polling API để lấy trạng thái, ảnh trang và các vùng. Người dùng có thể chỉnh vùng trước khi OCR.
7. Khi người dùng chọn chạy OCR, backend chuyển formula sang `ocr_queued` và đưa job vào hàng đợi.
8. Worker gọi pix2tex trên từng ảnh crop, lưu kết quả vào `latex_raw`.
9. Người dùng sửa LaTeX hoặc MathLive. Khi Submit, backend chỉ lưu bản cuối vào `latex_final`.

### Trạng thái cần hiểu

- Document thường đi qua: `processing_pages` → `detecting_formulas` → `formula_proposals_ready` → `ocr_processing` → `ocr_complete` hoặc `ocr_completed_with_errors`.
- Có thể gặp `processing_failed` nếu công đoạn render/detect lỗi. File ảnh upload không qua PDF pipeline có thể mang trạng thái `uploaded`.
- Formula đi qua: `proposed` → `ocr_queued` → `ocr_complete` hoặc `ocr_failed` → `submitted`.
- Chỉ formula còn ở `proposed` mới được sửa hoặc xóa vùng. Sau khi OCR bắt đầu, vùng được khóa để crop và kết quả OCR không bị lệch nhau.

---

## 3. Database hoạt động thế nào, và tại sao cần database?

### Database là gì trong dự án này?

Có thể hình dung PostgreSQL như một cuốn sổ theo dõi có cấu trúc. Nó không chỉ giữ một file vừa tải lên, mà còn trả lời được các câu hỏi như:

- Tài liệu này có ID nào, tên gốc là gì, đang ở bước nào?
- Một công thức thuộc tài liệu và trang nào?
- Crop nằm ở đâu, bbox là gì, confidence bao nhiêu?
- OCR đã tạo LaTeX nào? Người dùng đã sửa và xác nhận nội dung gì?
- Công thức đang chờ OCR, lỗi hay đã submit?

Nếu chỉ ghi tên file vào ổ đĩa mà không có database, backend sẽ khó tìm lại trạng thái và nối đúng crop/LaTeX với đúng tài liệu khi có nhiều lần upload hoặc nhiều job chạy đồng thời.

### Bốn bảng hiện có

| Bảng | Vai trò dễ hiểu | Một số trường chính |
|---|---|---|
| `documents` | Một hàng cho mỗi tài liệu được upload | `id`, `filename`, `status`, `uploaded_by`, `created_at` |
| `formula_entries` | Một hàng cho mỗi vùng/công thức tìm thấy | `id`, `document_id`, `page_number`, `image_path`, bbox, `confidence`, `latex_raw`, `latex_final`, `ocr_backend`, `status` |
| `users` | Khung lưu tài khoản cho chức năng người dùng sau này | `id`, `username`, `password_hash`, `created_at` |
| `logs` | Khung ghi sự kiện hoặc chi tiết kỹ thuật | `action`, `ref_id`, `detail` dạng JSONB, `created_at` |

Hiện luồng đăng nhập và ghi log chưa được tích hợp đầy đủ vào API. `users` và `logs` đã có model/migration nhưng chưa nên hiểu là ứng dụng đã có xác thực người dùng hoặc audit log hoàn chỉnh.

### Quan hệ tài liệu và công thức

Một tài liệu có thể chứa nhiều công thức. `formula_entries.document_id` là khóa ngoại trỏ tới `documents.id`:

```text
documents (1) -------- (n) formula_entries
```

`1` nghĩa là một document; `n` nghĩa là có thể có nhiều formula. Khóa ngoại giúp database không nhận formula thuộc một document không tồn tại.

### Vì sao `latex_raw` và `latex_final` là hai cột?

- `latex_raw`: kết quả do OCR sinh ra. Đây là mốc ban đầu để biết máy đã nhận dạng thế nào.
- `latex_final`: kết quả sau khi người dùng sửa và xác nhận.

Nếu sửa trực tiếp `latex_raw`, sẽ mất khả năng so sánh máy với người. Hai cột riêng cho phép tính BLEU hoặc edit-distance về sau và phân tích lỗi OCR.

### Model, schema, session và migration

- **Model SQLAlchemy** mô tả bảng trong Python: ví dụ `Document` tương ứng bảng `documents`.
- **Schema Pydantic** mô tả dữ liệu API nhận vào hoặc trả ra: ví dụ tọa độ bbox phải là số nguyên không âm.
- **Session** là một phiên làm việc ngắn với database. API lấy session qua `get_db()`, đọc/ghi dữ liệu, gọi `commit()` để lưu, rồi đóng session.
- **Migration Alembic** là lịch sử thay đổi cấu trúc bảng. Revision đầu tạo bảng; revision sau thêm bbox/confidence. Nếu cần đổi schema, hãy tạo revision mới, không sửa migration đã áp dụng.

### File, PostgreSQL và Redis không thay thế nhau

| Nơi lưu | Lưu cái gì? | Ví dụ |
|---|---|---|
| `backend/uploads/` | Nội dung file ảnh/PDF thật | `source.pdf`, `pages/page-000001.png`, `formulas/<uuid>.png` |
| PostgreSQL | Metadata, trạng thái, bbox và LaTeX | document ID, formula ID, `latex_raw`, `latex_final` |
| Redis/RQ | Việc worker chưa làm hoặc đang làm | job render, detect, recognize, retry |

Compose bật Redis AOF và volume `redisdata`; điều này hỗ trợ giữ dữ liệu Redis qua lần dừng bình thường. Khả năng phục hồi mọi job sau sự cố vẫn cần kiểm thử riêng, chưa được tuyên bố đảm bảo tuyệt đối.

---

## 4. Cấu trúc toàn bộ dự án

```text
Math2Latex/
|-- doc.md
|-- BaoCaoTienDoLan1_Math2Latex.docx
|-- docker-compose.yml
|-- package.json
|-- package-lock.json
|-- .gitignore
|-- tuan1.md
|-- tuan2.md
|-- week2-process.md
|-- backend/
|   |-- Dockerfile
|   |-- .dockerignore
|   |-- requirements.txt
|   |-- alembic.ini
|   |-- alembic/
|   |   |-- env.py
|   |   |-- README
|   |   |-- script.py.mako
|   |   `-- versions/
|   |       |-- 1c603257d451_create_initial_tables.py
|   |       `-- 7fd904b9f5b1_add_formula_region_bounds.py
|   |-- app/
|   |   |-- main.py
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   `-- documents.py
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- database.py
|   |   |   `-- queue.py
|   |   |-- models/
|   |   |   |-- __init__.py
|   |   |   |-- document.py
|   |   |   |-- formula_entry.py
|   |   |   |-- user.py
|   |   |   `-- log.py
|   |   |-- schemas/
|   |   |   |-- __init__.py
|   |   |   |-- document.py
|   |   |   `-- formula.py
|   |   `-- services/
|   |       |-- __init__.py
|   |       |-- pdf_pages.py
|   |       |-- formula_regions.py
|   |       `-- formula_ocr.py
|   `-- uploads/
|       |-- .gitkeep
|       `-- <document_uuid>/
|           |-- source.pdf
|           |-- pages/page-000001.png
|           `-- formulas/<formula_uuid>.png
|-- frontend/
|   |-- Dockerfile
|   |-- .gitignore
|   |-- package.json
|   |-- package-lock.json
|   |-- index.html
|   |-- vite.config.js
|   |-- eslint.config.js
|   |-- README.md
|   |-- scripts/copy-mathlive-fonts.mjs
|   |-- public/
|   |   |-- favicon.svg
|   |   |-- icons.svg
|   |   `-- mathlive-fonts/<các font KaTeX .woff2>
|   `-- src/
|       |-- main.jsx
|       |-- App.jsx
|       |-- App.css
|       |-- index.css
|       `-- assets/
|           |-- hero.png
|           |-- react.svg
|           `-- vite.svg
```

`backend/uploads/<document_uuid>/` là dữ liệu sinh ra khi chạy ứng dụng; mỗi máy có thể có nội dung khác nhau. Thư mục này được loại khỏi Git để không đưa PDF/crop người dùng lên repository. Cây trên gom các font KaTeX thành một nhóm cho dễ đọc; thư mục hiện chứa các font `.woff2` được MathLive dùng để hiển thị toán.

### File ở thư mục gốc

| File | Chức năng |
|---|---|
| `doc.md` | Tài liệu hướng dẫn và giải thích dự án hiện tại. |
| `BaoCaoTienDoLan1_Math2Latex.docx` | Báo cáo tiến độ lần 1 đã tạo cho buổi báo cáo. |
| `docker-compose.yml` | Khai báo các container PostgreSQL, Redis, backend, worker và frontend; port, volume, biến môi trường và kết nối giữa dịch vụ. |
| `package.json`, `package-lock.json` | Khai báo và khóa dependencies ở thư mục gốc. Ứng dụng React/Vite chính nằm trong `frontend/`. |
| `.gitignore` | Ngăn Git theo dõi upload, virtualenv, node_modules và file sinh ra. |


### Backend: từng file có chức năng gì?

| File | Chức năng và cách hiểu |
|---|---|
| `backend/Dockerfile` | Dựng môi trường Python cho API/worker, cài thư viện hệ thống cho OpenCV, dependencies Python và `onnxruntime-gpu`. |
| `backend/.dockerignore` | Loại virtualenv Windows, uploads và cache khỏi Docker build context để không đóng gói nhầm dữ liệu lớn hoặc môi trường không tương thích. |
| `backend/requirements.txt` | Danh sách thư viện Python cần cài: FastAPI, SQLAlchemy, Alembic, PyMuPDF, Pillow, Pix2Text, pix2tex và RQ/Redis. |
| `backend/alembic.ini` | Cấu hình Alembic, chỉ nơi chứa migrations và logging. URL thật được thay bằng `DB_URL` trong `env.py`. |
| `backend/app/main.py` | Tạo ứng dụng FastAPI, bật CORS cho môi trường phát triển, gắn router documents và khai báo `/health`. |
| `backend/app/api/documents.py` | Các API upload, đọc trang, quản lý formula/bbox/crop, queue recognize/retry và submit. Đây là lớp nhận HTTP và phối hợp model/service. |
| `backend/app/core/database.py` | Đọc `DB_URL`, tạo kết nối SQLAlchemy, `SessionLocal`, `Base` và dependency `get_db()` dùng theo từng request/job. |
| `backend/app/core/queue.py` | Tạo kết nối Redis, tên hàng RQ `math2latex`, và enqueue job với thời hạn/khoảng giữ kết quả. |
| `backend/app/models/document.py` | Định nghĩa bảng `documents`: UUID, tên file, trạng thái, người upload (hiện chưa liên kết đăng nhập) và thời gian tạo. |
| `backend/app/models/formula_entry.py` | Định nghĩa bảng `formula_entries`: liên kết document, trang, crop path, bbox, confidence, raw/final LaTeX và trạng thái. |
| `backend/app/models/user.py` | Định nghĩa cấu trúc bảng tài khoản dự kiến. Chưa đồng nghĩa với việc đã có API đăng ký/đăng nhập. |
| `backend/app/models/log.py` | Định nghĩa bảng log với nội dung chi tiết JSONB; hiện là nền tảng, chưa được gắn vào mọi thao tác API. |
| `backend/app/models/__init__.py` | Gom các model để import dễ dàng và giúp Alembic nhận diện tất cả bảng. |
| `backend/app/schemas/document.py` | Schema Pydantic cho response tài liệu, giúp quy định dữ liệu API trả về. |
| `backend/app/schemas/formula.py` | Schema đầu vào khi thêm/sửa bbox và submit LaTeX; kiểm tra số trang, tọa độ không âm và giới hạn độ dài LaTeX. |
| `backend/app/services/pdf_pages.py` | Mở PDF bằng PyMuPDF, render ảnh 150 DPI, gọi detector theo từng trang, ghi proposal xuống DB và cập nhật document status. |
| `backend/app/services/formula_regions.py` | Lazy-load Pix2Text MFD một lần trong worker, chuyển kết quả detector thành bbox pixel và tạo ảnh crop. |
| `backend/app/services/formula_ocr.py` | Lazy-load pix2tex, chọn CUDA nếu PyTorch thấy GPU (nếu không thì CPU), xử lý formula `ocr_queued`, ghi `latex_raw` và trạng thái thành công/lỗi. |
| `backend/app/api/__init__.py`, `core/__init__.py`, `models/__init__.py`, `schemas/__init__.py`, `services/__init__.py` | Đánh dấu các thư mục Python là package; một số file `__init__` gom model hoặc để trống nhằm giữ cấu trúc package. |
| `backend/alembic/env.py` | Nạp metadata model và URL `DB_URL`, để Alembic kết nối database và chạy migration. |
| `backend/alembic/versions/1c603257d451_create_initial_tables.py` | Migration đầu tiên tạo `documents`, `formula_entries`, `users`, `logs`. |
| `backend/alembic/versions/7fd904b9f5b1_add_formula_region_bounds.py` | Migration tiếp theo thêm `x_min`, `y_min`, `x_max`, `y_max`, `confidence` cho `formula_entries`. |
| `backend/alembic/script.py.mako` | Khuôn mẫu Alembic dùng khi tạo revision mới. |
| `backend/alembic/README` | Ghi chú mặc định của Alembic. |
| `backend/uploads/.gitkeep` | Giữ thư mục uploads rỗng trong Git; PDF, page PNG và crop sinh lúc chạy không được commit. |

### Frontend: từng file có chức năng gì?

| File | Chức năng và cách hiểu |
|---|---|
| `frontend/Dockerfile` | Cài Node dependencies và chạy Vite dev server trong container. |
| `frontend/package.json` | Khai báo React, React DOM, MathLive, Vite và lệnh `dev`, `build`, `lint`. |
| `frontend/package-lock.json` | Khóa phiên bản dependency để npm cài nhất quán. |
| `frontend/index.html` | Trang HTML ban đầu; có phần tử `#root` để React gắn ứng dụng vào. |
| `frontend/src/main.jsx` | Điểm khởi chạy React; tạo root và render `App`. |
| `frontend/src/App.jsx` | Luồng UI chính: upload, polling, hiển thị trang/bbox, chỉnh vùng, chạy OCR, đồng bộ textarea/MathLive và submit. |
| `frontend/src/App.css` | Style workspace, trang PDF, overlay bbox, panel công thức và editor. |
| `frontend/src/index.css` | Style toàn cục: font, màu nền, box sizing, focus keyboard và vùng React root. |
| `frontend/vite.config.js` | Cấu hình Vite và plugin React. |
| `frontend/eslint.config.js` | Quy tắc lint JavaScript/JSX và React hooks. |
| `frontend/scripts/copy-mathlive-fonts.mjs` | Sao chép font MathLive từ `node_modules` sang `public/mathlive-fonts` trước dev/build. |
| `frontend/public/mathlive-fonts/*.woff2` | Font KaTeX/MathLive để ký hiệu toán render đúng trong trình duyệt. Thư mục này được script tạo/cập nhật. |
| `frontend/public/favicon.svg`, `icons.svg` | Tài nguyên SVG tĩnh được phục vụ nguyên trạng từ thư mục public. |
| `frontend/src/assets/hero.png`, `react.svg`, `vite.svg` | Tài nguyên đi kèm cấu trúc frontend; không phải thành phần pipeline backend. |
| `frontend/.gitignore` | Bỏ qua node_modules, dist và font được script sinh ra. |
| `frontend/README.md` | README mẫu do Vite tạo; một số hướng dẫn có thể chưa phản ánh Math2Latex. |

---

## 5. API chính để làm quen

| Method và đường dẫn | Nói đơn giản là |
|---|---|
| `GET /health` | Kiểm tra backend có đang chạy không. |
| `POST /api/documents/upload` | Gửi file lên; PDF tạo document và enqueue render/detect. |
| `GET /api/documents/{id}/pages` | Lấy trạng thái document và danh sách trang/kích thước ảnh. |
| `GET /api/documents/{id}/pages/{page_number}` | Tải ảnh một trang PDF. |
| `GET /api/documents/{id}/formulas` | Lấy các vùng công thức và kết quả LaTeX. |
| `POST /api/documents/{id}/formulas` | Thêm bbox thủ công. |
| `PATCH /api/documents/{id}/formulas/{formula_id}` | Sửa bbox proposal. |
| `DELETE /api/documents/{id}/formulas/{formula_id}` | Xóa proposal và crop tương ứng. |
| `GET /api/documents/{id}/formulas/{formula_id}/image` | Xem ảnh crop của một formula. |
| `POST /api/documents/{id}/formulas/recognize` | Queue OCR cho các proposal. |
| `POST /api/documents/{id}/formulas/retry` | Queue lại formula có trạng thái OCR lỗi. |
| `POST /api/documents/{id}/formulas/{formula_id}/submit` | Lưu LaTeX đã được người dùng xác nhận. |

FastAPI sinh tài liệu tương tác tại `/docs`; có thể gọi thử endpoint và xem schema request/response ở đó.

---

## 6. Cách chạy dự án trên Windows

### Cần chuẩn bị

1. Cài và mở Docker Desktop, dùng Linux containers/WSL 2.
2. Cài NVIDIA driver nếu muốn dùng GPU. Compose hiện khai báo `gpus: all` cho worker; Docker phải cấp GPU được.
3. Có Internet ở lần đầu để tải Docker images và model weights.
4. Mở PowerShell ở thư mục gốc `D:\Math2Latex`.

### Khởi động lần đầu hoặc sau khi đổi Dockerfile/dependencies

```powershell
docker compose config -q
docker compose up -d --build
docker compose ps
```

Chờ `db` và `redis` healthy, các service `backend`, `worker`, `frontend` running. Lần đầu tạo database hoặc sau khi thêm migration, chạy:

```powershell
docker compose exec backend alembic upgrade head
```

Lệnh này tạo/cập nhật bảng. Alembic chỉ chạy khi được gọi; Compose không tự chạy migration mỗi lần khởi động.

### Mở webapp

- Ứng dụng: <http://localhost:5173>
- Kiểm tra API: <http://localhost:8000/health>
- Tài liệu API: <http://localhost:8000/docs>

Trong app: chọn PDF → tải lên → chờ tách trang và đề xuất bbox → rà/chỉnh vùng → chạy OCR → sửa LaTeX hoặc MathLive → Submit. Lần đầu model có thể mất thời gian tải; theo dõi worker bằng:

```powershell
docker compose logs -f worker
```

Theo dõi các service khác:

```powershell
docker compose logs -f backend frontend db redis
```

Dừng chế độ theo dõi bằng `Ctrl+C`; lệnh này chỉ ngừng xem log, không dừng container.

### Những lần chạy sau

```powershell
docker compose up -d
docker compose ps
```

Nếu đã có database, không cần chạy lại migration trừ khi có revision mới. Dừng ứng dụng mà giữ dữ liệu:

```powershell
docker compose down
```

Không thêm `-v` nếu muốn giữ volume `pgdata` và `redisdata`. `docker compose down -v` xóa volume database/Redis; thao tác đó có thể làm mất dữ liệu.

### Khi có lỗi thường gặp

- **Port 5173, 8000 hoặc 5432 đang được dùng:** xem `docker compose ps`, đóng ứng dụng khác đang chiếm port hoặc đổi port mapping.
- **Backend báo thiếu `DB_URL`:** chạy qua Compose để biến môi trường được thiết lập; chạy Python trực tiếp cần tự cấu hình `DB_URL` và `REDIS_URL`.
- **Bảng chưa tồn tại:** kiểm tra DB healthy rồi chạy `docker compose exec backend alembic upgrade head`.
- **Web upload được nhưng không xử lý xong:** xem `docker compose logs -f worker redis`; kiểm tra Redis healthy và worker running.
- **GPU không nhận:** thử `nvidia-smi` trên Windows, sau đó lệnh test CUDA container trong mục tiếp theo. Worker cần Docker Desktop GPU support; `torch.cuda.is_available()` cần là `True` để pix2tex chọn CUDA.
- **Model tải lỗi:** kiểm tra Internet/Hugging Face và log worker. Đừng xóa database/volume để xử lý lỗi tải model.
- **Frontend không kết nối API:** app dev đang gọi `http://localhost:8000` trực tiếp; kiểm tra backend và port 8000.

### Kiểm tra GPU độc lập

```powershell
nvidia-smi
docker run --rm --gpus all nvidia/cuda:13.0.0-base-ubuntu24.04 nvidia-smi
```

Trong Compose, worker dùng `MATH_DETECTOR_DEVICE=cuda`, MFD backend `onnx`, PyTorch của pix2tex tự chọn CUDA khi khả dụng. GPU đã được smoke test trên máy phát triển. ONNX Runtime từng đưa ra cảnh báo plugin EP, nên nếu cần chứng minh toàn bộ phép tính MFD chạy CUDA hãy profile thêm; không dùng kết quả smoke test thay cho benchmark OCR.

---

## 7. Thứ tự học để dễ hiểu code

1. Đọc mục tiêu và sơ đồ pipeline trong tài liệu này.
2. Mở `docker-compose.yml` để thấy các service kết nối với nhau.
3. Đọc `backend/app/main.py`, rồi `backend/app/api/documents.py` để hiểu HTTP API.
4. Đọc `backend/app/core/database.py` và các file trong `models/` để hiểu dữ liệu lưu ra sao.
5. Đọc `backend/app/core/queue.py` để hiểu job được chuyển cho worker thế nào.
6. Đọc `pdf_pages.py`, `formula_regions.py`, `formula_ocr.py` theo thứ tự pipeline.
7. Đọc `frontend/src/main.jsx`, rồi `App.jsx`; xem CSS sau khi hiểu state và request.
8. Dùng <http://localhost:8000/docs> thử endpoint health và xem request schema.
9. Chạy demo với một PDF nhỏ trước khi dùng tài liệu lớn.

### Bốn khái niệm cần nhớ

- **API**: cửa giao tiếp HTTP giữa trình duyệt và backend.
- **Model**: định nghĩa bảng database bằng class Python.
- **Schema**: định dạng dữ liệu API cho phép nhận/trả.
- **Service/worker**: nơi thực hiện công việc nghiệp vụ hoặc tác vụ lâu, không để request chờ lâu.

---

## 8. Giới hạn hiện tại và việc tiếp theo

- Chưa có tập PDF toán nhiều trang kèm LaTeX chuẩn để tính BLEU/edit-distance.
- OCR có thể nhận sai; người dùng cần rà và chỉnh trước khi Submit.
- MFD ONNX session có CUDA provider nhưng còn warning runtime; cần profile sâu hơn để xác nhận node thực sự chạy trên GPU.
- Redis AOF/volume đã cấu hình; khả năng phục hồi job sau restart/crash chưa được kiểm thử.
- Frontend build/lint đã qua; cần kiểm tra font MathLive trực quan sau refresh container.
- Login, phân quyền và ghi log đầy đủ chưa được triển khai dù đã có bảng `users`, `logs`.
- Không sửa migration đã áp dụng. Tạo migration Alembic mới khi đổi schema database.


