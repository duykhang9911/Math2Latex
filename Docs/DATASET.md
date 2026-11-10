# Dữ liệu PDF dùng để kiểm thử và đánh giá

Dữ liệu của đồ án là các PDF mà chủ dự án đã upload vào ứng dụng khi chạy dự án. Chúng nằm trong PostgreSQL (`documents`, `formula_entries`) và `backend/uploads/<document_id>/source.pdf`, thư mục này bị Git bỏ qua. PDF không được commit vào Git. Manifest chi tiết (bbox, LaTeX chuẩn) làm ở task S5-01 trong [PHAN_CONG_CONG_VIEC](PHAN_CONG_CONG_VIEC.md).

Chủ dự án xác nhận ngày 2026-11-10: được dùng các tài liệu đã upload làm dữ liệu. Riêng các file `*-MathMethods1.pdf`, chủ dự án cho biết là đề thi của bang Victoria (Australia) đã được sử dụng ở các năm trước và được công bố công khai. Nguồn của các file còn lại chưa được ghi; chưa có số hiệu giấy phép hay đường dẫn trang gốc, bổ sung khi có.

## Tài liệu hiện có (kiểm tra trong database ngày 2026-11-10)

| File | Số lần upload | Vùng công thức đã detect (mỗi lần) | Ghi chú |
|---|---|---|---|
| `2017-MathMethods1.pdf` | 7 | 103–130 | Một lần có `page_count` = 15; hầu hết đã OCR |
| `2025-MathMethods1.pdf` | 1 | 107 | Đã OCR |
| `de-chinh-thuc-ky-thi-tot-nghiep-thpt-nam-2026-lan-2-mon-toan.pdf` | 3 | 137–387 | Hai lần dừng ở `formula_proposals_ready`, một lần đã OCR |
| `test.pdf`, `Lab 01.pdf` | 3 + 1 | 0 | Chưa xử lý; chưa xác định có dùng được cho đánh giá |

Một file được upload nhiều lần nên số vùng/trạng thái khác nhau giữa các lần (vùng đã sửa tay, chạy lại OCR). Khi lập manifest S5-01, chọn một document làm bản chuẩn cho mỗi file và ghi `document_id` ở đây.

14 trong 15 document có `uploaded_by` rỗng (upload trước khi có tài khoản) nên không hiện trong lịch sử của ai; chỉ API/SQL đọc được. Xử lý owner theo quyết định D-07.

## Quy tắc

- Không commit PDF, crop, ảnh trang vào Git.
- Không xóa các document và thư mục `backend/uploads/<document_id>/` này, kể cả khi làm retention/cleanup (S3-03) hoặc `docker compose down -v`. Sao lưu `backend/uploads/` và database ra ngoài repository trước khi dọn dẹp.
- Mỗi file mới phải ghi nguồn và người xác nhận quyền dùng vào bảng trên.
- Dữ liệu tổng hợp chỉ dùng để kiểm thử chức năng, không dùng để kết luận độ chính xác.
