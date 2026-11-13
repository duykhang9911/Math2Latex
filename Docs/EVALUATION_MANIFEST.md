# Manifest dữ liệu đánh giá — Math2Latex (S5-01)

> **Lập ngày:** 2026-11-13
> **Phiên bản:** 1.0

## 1. Nguồn dữ liệu

Dữ liệu đánh giá gồm các file PDF đã upload vào ứng dụng Math2Latex trong quá trình phát triển. Chủ dự án xác nhận quyền sử dụng ngày 2026-11-10 (xem [DATASET.md](../DATASET.md)).

## 2. Danh sách tài liệu

| # | Filename | Loại | Số trang | Bbox (detect) | LaTeX chuẩn | Nguồn | Ghi chú |
|---|---|---|---|---|---|---|---|
| 1 | `2017-MathMethods1.pdf` | Scan, display math, inline | 15 | 103–130 | Chưa review | Đề thi bang Victoria (Australia) 2017, công khai | 7 lần upload; chọn bản đã OCR xong làm chuẩn |
| 2 | `2025-MathMethods1.pdf` | Scan, display math, inline | ~15 | 107 | Chưa review | Đề thi bang Victoria (Australia) 2025, công khai | 1 lần upload, đã OCR |
| 3 | `de-chinh-thuc-ky-thi-tot-nghiep-thpt-nam-2026-lan-2-mon-toan.pdf` | Scan/vector, display + inline | ~6 | 137–387 | Chưa review | Đề thi tốt nghiệp THPT Việt Nam 2026, công khai | 3 lần upload; 1 lần đã OCR |
| 4 | `Công thức Toán 12 thầy Đạt Full.pdf` | Vector, display math dense | 55 | 1709 | Chưa review | Nguồn chưa ghi rõ | Hiện còn trong DB |
| 5 | `test.pdf` | Không xác định | — | 0 | — | — | Không dùng cho đánh giá |
| 6 | `Lab 01.pdf` | Không xác định | — | 0 | — | — | Không dùng cho đánh giá |

### 2.1 Document ID bản chuẩn

| Filename | Document ID chuẩn | Trạng thái |
|---|---|---|
| `Công thức Toán 12 thầy Đạt Full.pdf` | `78037cc5-287b-4ab9-a183-fc53a396fbaa` | `formula_proposals_ready` (1709 vùng, 0 submitted) |

> [!NOTE]
> Các document khác đã bị mất do `docker compose down -v`. Bản backup tại `D:\Math2Latex_backup\20261110-1747\` (uploads 1826 file, 28.8 MB + `math2latex.dump`). Cần khôi phục backup (`pg_restore`) để có đủ 15 document/1669 công thức.

## 3. Phân loại tài liệu

| Đặc điểm | File áp dụng |
|---|---|
| **Scan** (ảnh quét) | MathMethods1 2017/2025, đề thi THPT |
| **Vector** (PDF text layer) | Công thức Toán 12 |
| **Display math** (công thức độc lập) | Tất cả |
| **Inline math** (công thức trong dòng) | MathMethods1, đề thi THPT |
| **Nhiều cột** | Không có |
| **Dense formula** (nhiều công thức/trang) | Công thức Toán 12 (~31 vùng/trang) |

## 4. Quy trình lập đáp án chuẩn (ground truth)

1. Chạy ứng dụng detect + OCR trên từng document
2. Mở giao diện review, so sánh crop ảnh với `latex_raw`
3. Sửa LaTeX bằng tay → Submit → `latex_final` là đáp án chuẩn
4. Export query SQL: `SELECT formula_id, latex_raw, latex_final FROM formula_entries WHERE status='submitted' AND document_id=?`

## 5. Quyền dùng dữ liệu

| File | Quyền | Xác nhận |
|---|---|---|
| `*-MathMethods1.pdf` | Đề thi công khai bang Victoria | Chủ dự án 2026-11-10 |
| `de-chinh-thuc-*-mon-toan.pdf` | Đề thi công khai Bộ GD&ĐT VN | Chủ dự án 2026-11-10 |
| `Công thức Toán 12 thầy Đạt Full.pdf` | Chưa rõ nguồn gốc | Cần bổ sung |

## 6. Hạn chế

- Chưa có LaTeX ground truth (chưa review thủ công đáp án chuẩn cho bất kỳ document nào)
- Dữ liệu gốc (15 document) cần khôi phục từ backup
- Chưa có bbox ground truth thủ công để đo IoU detector
- Số lượng file ít (3–4 file có ý nghĩa), chưa đa dạng (chỉ có đề thi toán)

