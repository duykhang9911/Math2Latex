# Frontend Tests — Math2Latex

## Test Runner

[Vitest](https://vitest.dev/) — tích hợp sẵn với Vite, hỗ trợ ESM, JSX và jsdom.

## Lệnh chạy

```bash
# Chạy một lần (CI)
npm run test

# Chế độ watch (dev)
npm run test:watch

# Mở Vitest UI
npx vitest --ui
```

## Bố trí thư mục

```
frontend/
├── src/
│   └── test-setup.js          # Import @testing-library/jest-dom
├── tests/
│   ├── README.md              # File này
│   ├── formula-editor/
│   │   └── FormulaEditor.test.jsx
│   ├── region-overlay/
│   │   └── RegionOverlay.test.jsx
│   └── document-flow/
│       └── DocumentFlow.test.jsx
└── vite.config.js             # Cấu hình test: environment jsdom, globals true
```

## Cấu hình

- **environment:** `jsdom` — giả lập DOM trong Node.js
- **globals:** `true` — không cần import `describe/it/expect` thủ công
- **setupFiles:** `./src/test-setup.js` — tự động import jest-dom matchers

## Thư viện

| Thư viện | Mục đích |
|---|---|
| `vitest` | Test runner chính |
| `@vitest/ui` | Giao diện web xem kết quả test |
| `jsdom` | Giả lập môi trường trình duyệt |
| `@testing-library/react` | Render và query React components |
| `@testing-library/jest-dom` | Matchers DOM bổ sung (`toBeInTheDocument`, v.v.) |
| `@testing-library/user-event` | Giả lập tương tác người dùng |
