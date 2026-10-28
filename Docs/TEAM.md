# Nhóm và vai trò

Hai thành viên đã xác nhận. MSSV, nhóm/lớp, giảng viên, deadline và vai trò nhóm trưởng chưa được cung cấp nên để trống; không tự điền dữ liệu.

| Thành viên | Owner chính | Owner hỗ trợ | Review chéo |
|---|---|---|---|
| Đoàn Trương Duy Khang | Backend/API, PostgreSQL/Alembic, Redis/RQ, Docker/GPU runtime, xử lý PDF/MFD/OCR | Review API và state với frontend; hỗ trợ integration/demo | Review frontend/API contract và test người dùng của Ngô Hồ Tuấn Toàn |
| Ngô Hồ Tuấn Toàn | Frontend/MathLive, accessibility, browser tests, bộ PDF đánh giá, tài liệu và demo | Thu thập PDF có quyền dùng; kiểm thử end-to-end/accuracy cùng backend | Review service/API behavior, bbox và dữ liệu persistence của Đoàn Trương Duy Khang |

## Quy tắc phối hợp

- Mỗi task trong backlog có đúng một owner chính; người còn lại là reviewer hoặc hỗ trợ theo dependency.
- Chốt API/schema/status transition cùng nhau trước khi hai phần frontend/backend triển khai song song.
- Duy Khang không tự kết luận độ chính xác OCR; Tuấn Toàn không sửa business state chỉ ở UI để che lỗi backend.
- Hai thành viên cùng xác nhận demo cuối và ghi rõ blocker/runtime limitation.

## Thông tin nhóm cần bổ sung

- MSSV của mỗi thành viên.
- Lớp/môn học, nhóm số, giảng viên hướng dẫn và deadline.
- Nhóm trưởng/người nộp báo cáo.