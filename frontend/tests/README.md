# Frontend tests

Browser/component test suite chính thức chưa được cấu hình. Bố trí đề xuất khi chọn test runner:

```text
tests/
|-- formula-editor/     # LaTeX <-> MathLive synchronization, submit states
|-- region-overlay/     # pointer/keyboard move and resize, bounds
`-- document-flow/      # upload, polling, OCR success/failure/retry
```

Ưu tiên test contract và user interaction; API thật dùng test environment riêng. Không coi mock browser run là integration test database.