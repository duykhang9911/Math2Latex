# Sơ đồ hệ thống

Sơ đồ vẽ bằng Mermaid (GitHub và VS Code hiển thị được). Nội dung lấy từ mã nguồn ngày 2026-11-10; khi đổi model, trạng thái hoặc Compose phải sửa lại cùng PR. Các sơ đồ này **chưa được render thử bằng công cụ Mermaid** trong môi trường phát triển; nếu có lỗi cú pháp, sửa theo thông báo của trình xem.

## 1. Chức năng theo tác nhân

```mermaid
flowchart LR
  U([Người dùng])
  W([Worker RQ])

  subgraph FR0[FR0 Tài khoản]
    A1[Đăng ký] --- A2[Đăng nhập] --- A3[Đăng xuất]
  end
  subgraph FR1[FR1 PDF thành đề xuất vùng và latex_raw]
    B1[Upload PDF] --> B2[Thêm/sửa/xóa vùng] --> B3[Xác nhận vùng chạy OCR]
  end
  subgraph FR2[FR2 Chỉnh sửa hai chiều]
    C1[Sửa LaTeX và MathLive đồng bộ]
  end
  subgraph FR3[FR3 Submit]
    D1[Submit ghi latex_final]
  end
  subgraph FR4[FR4 Lịch sử và xuất]
    E1[Xem/mở/xóa lịch sử] --- E2[Tải PDF gốc] --- E3[Xuất .tex]
  end

  U --> FR0
  U --> FR1
  U --> FR2
  U --> FR3
  U --> FR4
  W -.render, detect, OCR.-> B1
  W -.OCR.-> B3
```

## 2. Kiến trúc và triển khai (Docker Compose)

```mermaid
flowchart LR
  Browser[Trình duyệt<br/>React + MathLive]
  subgraph Compose[Docker Compose - máy phát triển]
    FE[frontend<br/>Vite :5173]
    API[backend<br/>FastAPI/uvicorn :8000]
    WK[worker<br/>rq worker, queue math2latex]
    DB[(db<br/>PostgreSQL 16 :5432<br/>volume pgdata)]
    RD[(redis 7<br/>AOF, volume redisdata)]
    FS[/backend/uploads<br/>bind mount ./backend/]
  end
  Browser -->|HTTP| FE
  Browser -->|HTTP + cookie HttpOnly| API
  API -->|SQLAlchemy| DB
  API -->|enqueue + on_failure| RD
  RD --> WK
  WK -->|trạng thái, công thức| DB
  API --> FS
  WK -->|PyMuPDF, Pix2Text MFD, pix2tex| FS
```

## 3. Luồng upload → OCR → Submit

```mermaid
sequenceDiagram
  actor U as Người dùng
  participant FE as Frontend
  participant API as FastAPI
  participant DB as PostgreSQL
  participant Q as Redis/RQ
  participant W as Worker

  U->>FE: chọn PDF
  FE->>API: POST /api/documents/upload
  API->>API: kiểm tra PDF thật, mật khẩu, số trang, pixel
  API->>DB: document processing_pages
  API->>Q: enqueue process_pdf_pages
  API-->>FE: 200 document_id
  Q->>W: job
  W->>W: render trang, detect vùng, cắt crop
  W->>DB: formula proposed, document formula_proposals_ready
  loop polling
    FE->>API: GET document, pages, formulas
  end
  U->>FE: sửa vùng (thêm/di chuyển/xóa)
  FE->>API: POST/PATCH/DELETE /formulas
  U->>FE: xác nhận vùng
  FE->>API: POST /formulas/recognize
  API->>DB: formula ocr_queued, document ocr_processing
  API->>Q: enqueue process_formula_ocr
  API-->>FE: 202
  Q->>W: job
  W->>DB: latex_raw, formula ocr_complete hoặc ocr_failed
  U->>FE: sửa LaTeX/MathLive
  U->>FE: Submit
  FE->>API: POST /formulas/{id}/submit
  API->>DB: latex_final, status submitted (latex_raw giữ nguyên)
  API-->>FE: 200
```

## 4. Trạng thái

```mermaid
stateDiagram-v2
  direction LR
  [*] --> processing_pages: upload
  processing_pages --> detecting_formulas: render xong
  detecting_formulas --> formula_proposals_ready: detect xong
  processing_pages --> processing_failed: lỗi hoặc job bị bỏ rơi
  detecting_formulas --> processing_failed: lỗi hoặc job bị bỏ rơi
  formula_proposals_ready --> ocr_processing: recognize
  ocr_processing --> ocr_complete: mọi công thức OCR xong
  ocr_processing --> ocr_completed_with_errors: có công thức lỗi hoặc job bị bỏ rơi
  ocr_completed_with_errors --> ocr_processing: retry
```

```mermaid
stateDiagram-v2
  direction LR
  [*] --> proposed: detect hoặc thêm tay
  proposed --> ocr_queued: recognize
  ocr_queued --> ocr_complete: OCR thành công
  ocr_queued --> ocr_failed: OCR lỗi hoặc job bị bỏ rơi
  ocr_failed --> ocr_queued: retry
  ocr_complete --> submitted: Submit
  submitted --> submitted: Submit lại
```

Document cũ có thể ở trạng thái `uploaded` (trước khi có pipeline nền). Chỉ công thức `proposed` mới sửa/xóa được vùng.

## 5. Mô hình dữ liệu

```mermaid
erDiagram
  USERS ||--o{ DOCUMENTS : "uploaded_by (SET NULL)"
  USERS ||--o{ LOGS : "user_id (SET NULL)"
  DOCUMENTS ||--o{ FORMULA_ENTRIES : "document_id"

  USERS {
    uuid id PK
    string username UK
    string password_hash
    datetime created_at
  }
  DOCUMENTS {
    uuid id PK
    string filename
    string status "CHECK ck_documents_status"
    uuid uploaded_by FK
    bigint file_size_bytes
    int page_count
    datetime created_at
    datetime updated_at
  }
  FORMULA_ENTRIES {
    uuid id PK
    uuid document_id FK
    int page_number "từ 1"
    string image_path
    int x_min
    int y_min
    int x_max
    int y_max
    float confidence
    text latex_raw "OCR, bất biến"
    text latex_final "chỉ Submit ghi"
    string ocr_backend
    string status "CHECK ck_formula_entries_status"
    datetime created_at
  }
  LOGS {
    uuid id PK
    string action
    uuid ref_id
    jsonb detail
    uuid user_id FK
    datetime created_at
  }
```

Tọa độ bbox là pixel của ảnh trang đã render (150 dpi). File PDF, ảnh trang và crop nằm ở `UPLOAD_DIR/<document_id>/` ngoài database.
