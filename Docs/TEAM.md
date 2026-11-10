# Nhóm và vai trò

Hai thành viên đã xác nhận; MSSV và lớp lấy từ thông tin nhóm cung cấp. Môn học, nhóm số, giảng viên hướng dẫn, deadline và vai trò nhóm trưởng chưa được cung cấp nên để trống; không tự điền dữ liệu.

| Thành viên | MSSV | Lớp | Owner chính | Owner hỗ trợ | Review chéo |
|---|---|---|---|---|---|
| Đoàn Trương Duy Khang | 2111844 | CTK45A | Backend/API, PostgreSQL/Alembic, Redis/RQ, Docker/GPU runtime, xử lý PDF/MFD/OCR | Review API và state với frontend; hỗ trợ integration/demo | Review frontend/API contract và test người dùng của Ngô Hồ Tấn Toàn |
| Ngô Hồ Tấn Toàn | 2212473 | CTK46A | Frontend/MathLive, accessibility, browser tests, bộ PDF đánh giá, tài liệu và demo | Thu thập PDF có quyền dùng; kiểm thử end-to-end/accuracy cùng backend | Review service/API behavior, bbox và dữ liệu persistence của Đoàn Trương Duy Khang |

Phân công theo từng sprint nằm ở [PHAN_CONG_CONG_VIEC](PHAN_CONG_CONG_VIEC.md) mục 3.3. Trong tài liệu đó "Khang" là Đoàn Trương Duy Khang và "Toàn" là Ngô Hồ Tấn Toàn.

## Quy tắc phối hợp

- Mỗi task trong backlog có đúng một owner chính; người còn lại là reviewer hoặc hỗ trợ theo dependency.
- Chốt API/schema/status transition cùng nhau trước khi hai phần frontend/backend triển khai song song.
- Đoàn Trương Duy Khang không tự kết luận độ chính xác OCR; Ngô Hồ Tấn Toàn không sửa business state chỉ ở UI để che lỗi backend.
- Công việc của Ngô Hồ Tấn Toàn được làm và push trên GitHub của Toàn; cách tích hợp vào repository chính do hai thành viên chốt (quyết định D-11), mặc định theo [GIT_WORKFLOW](GIT_WORKFLOW.md) có review chéo.
- Hai thành viên cùng xác nhận demo cuối và ghi rõ blocker/runtime limitation.

## Thông tin nhóm cần bổ sung

- Môn học, nhóm số, giảng viên hướng dẫn và deadline.
- Nhóm trưởng/người nộp báo cáo.