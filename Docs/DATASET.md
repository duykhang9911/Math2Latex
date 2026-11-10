# Dữ liệu PDF dùng để kiểm thử và đánh giá

Danh sách nguồn và quyền sử dụng của PDF toán. PDF không được commit vào Git; mỗi thành viên giữ bản của mình ở vị trí ngoài repository. Manifest chi tiết (bbox, LaTeX chuẩn) làm ở task S5-01 trong [PHAN_CONG_CONG_VIEC](PHAN_CONG_CONG_VIEC.md).

## Nguồn đã xác nhận

Chủ dự án xác nhận ngày 2026-11-10: các file dưới đây là đề thi của bang Victoria (Australia) đã được sử dụng ở các năm trước, là tài liệu được công bố công khai và được phép dùng cho đồ án. Chưa ghi số hiệu giấy phép hay đường dẫn trang gốc; bổ sung khi có.

| Mã | File | Kích thước | Số trang | Vị trí lưu (ngoài Git) | Mục đích |
|---|---|---|---|---|---|
| DS-2020 | `2020-MathMethods1.pdf` | 850 KB | chưa đo | `d:\duanchiDuong\` | Kiểm tra pipeline; ứng viên đánh giá |
| DS-2022 | `2022-MathMethods1.pdf` | 703 KB | 17 | `d:\duanchiDuong\` | Kiểm tra pipeline; ứng viên đánh giá |
| DS-2025 | `2025-MathMethods1.pdf` | 874 KB | chưa đo | `d:\DOANTN\` | Kiểm tra pipeline; ứng viên đánh giá |

Số trang của DS-2022 do backend báo sau khi upload. DS-2022 đã dùng cho smoke test chức năng (S1-07), không phải đo độ chính xác.

## Chưa đủ cho đánh giá

Ba file cùng một loại đề thi nên chưa đủ đa dạng theo S5-01 (cần thêm bản scan, bố cục nhiều cột, công thức inline lẫn trong câu). Cần bổ sung nguồn khác và xác nhận quyền dùng trước khi kết luận độ chính xác.

## Quy tắc

- Không commit PDF, crop, ảnh trang vào Git (`backend/uploads/` đã bị ignore).
- Mỗi file mới phải ghi nguồn và người xác nhận quyền dùng vào bảng trên.
- Dữ liệu tổng hợp chỉ dùng để kiểm thử chức năng, không dùng để kết luận độ chính xác.
