# Backend tests

Test suite chính thức chưa được thiết lập. Khi thêm test, tổ chức đề xuất:

```text
tests/
|-- unit/          # bbox, status transitions, service behavior với fake model
|-- api/           # FastAPI route + PostgreSQL test database
|-- worker/        # RQ enqueue, retries, failure/restart behavior
`-- fixtures/      # chỉ dữ liệu synthetic hoặc PDF được phép dùng
```

Không lưu PDF/crop cá nhân hoặc model weights trong fixtures. Test GPU/real model nên opt-in, không làm unit test mặc định phụ thuộc CUDA hoặc Internet.