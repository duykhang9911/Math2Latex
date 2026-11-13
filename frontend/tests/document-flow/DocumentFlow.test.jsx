import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from '../../src/App'

// --- Mocks ---

// Mock MathLive custom element
if (!customElements.get('math-field')) {
  customElements.define('math-field', class extends HTMLElement {
    get value() { return this.getAttribute('value') || '' }
    set value(v) { this.setAttribute('value', v) }
  })
}

// Track fetch calls
let fetchCalls = []

const mockUser = { id: 1, username: 'testuser' }

const mockDocument = {
  document_id: 'doc-1',
  filename: 'test.pdf',
  status: 'uploaded',
  file_size_bytes: 102400,
  page_count: 2,
  formula_count: 0,
  submitted_count: 0,
  created_at: '2026-01-01T00:00:00Z',
}

const mockPages = {
  pages: [
    { page_number: 1, width: 1000, height: 1400, image_url: '/api/documents/doc-1/pages/1/image' },
  ],
}

const mockFormulas = {
  status: 'formula_proposals_ready',
  formulas: [
    {
      formula_id: 'f-1',
      page_number: 1,
      status: 'proposed',
      confidence: 0.9,
      latex_raw: null,
      latex_final: null,
      bounds: { x_min: 10, y_min: 20, x_max: 100, y_max: 80 },
      image_url: '/api/documents/doc-1/formulas/f-1/image',
    },
  ],
}

const mockHistory = { items: [], total: 0 }

function makeFetchResponse(data, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => data,
    blob: async () => new Blob([JSON.stringify(data)]),
    clone: function() { return this },
  }
}

function setupFetch(overrides = {}) {
  const responses = {
    '/api/auth/me': () => makeFetchResponse(mockUser),
    '/api/documents?limit=10&offset=0': () => makeFetchResponse(mockHistory),
    '/api/documents/upload': () => makeFetchResponse({ document_id: 'doc-1', status: 'uploaded' }),
    '/api/documents/doc-1': () => makeFetchResponse(mockDocument),
    '/api/documents/doc-1/pages': () => makeFetchResponse(mockPages),
    '/api/documents/doc-1/formulas': () => makeFetchResponse(mockFormulas),
    '/api/documents/doc-1/formulas/recognize': () => makeFetchResponse({ status: 'ocr_processing', queued_count: 1 }),
    '/api/documents/doc-1/formulas/retry': () => makeFetchResponse({ status: 'ocr_processing', queued_count: 1 }),
    '/api/documents/doc-1/formulas/f-1/submit': () => makeFetchResponse({ status: 'submitted', latex_raw: '\\frac{x}{y}', latex_final: '\\frac{x}{y}' }),
    ...overrides,
  }

  globalThis.fetch = vi.fn(async (url, options = {}) => {
    fetchCalls.push({ url: url.toString(), options })
    const path = new URL(url).pathname + (new URL(url).search || '')
    for (const [pattern, handler] of Object.entries(responses)) {
      if (path.includes(pattern) || path.endsWith(pattern)) {
        return handler()
      }
    }
    return makeFetchResponse({ detail: 'Not found' }, false, 404)
  })
}

beforeEach(() => {
  fetchCalls = []
  setupFetch()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DocumentFlow (S4-04)', () => {
  describe('authentication', () => {
    it('renders loading state initially', () => {
      // Override /me to never resolve, simulating loading
      globalThis.fetch = vi.fn(() => new Promise(() => {}))
      render(<App />)
      expect(screen.getByText('Đang kiểm tra phiên đăng nhập…')).toBeInTheDocument()
    })

    it('shows login form when user is not authenticated', async () => {
      setupFetch({
        '/api/auth/me': () => makeFetchResponse({ detail: 'Unauthorized' }, false, 401),
      })
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('Chào mừng trở lại.')).toBeInTheDocument()
      })
    })

    it('shows workspace when user is authenticated', async () => {
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument()
      })
    })

    it('shows register form when clicking toggle', async () => {
      setupFetch({
        '/api/auth/me': () => makeFetchResponse({ detail: 'Unauthorized' }, false, 401),
      })
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('Đăng ký')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('Đăng ký'))
      expect(screen.getByText('Tạo tài khoản.')).toBeInTheDocument()
    })
  })

  describe('upload', () => {
    it('renders upload form after login', async () => {
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('Chọn PDF để bắt đầu')).toBeInTheDocument()
      })
    })

    it('upload button is disabled when no file selected', async () => {
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText(/Tải PDF/)).toBeDisabled()
      })
    })
  })

  describe('history', () => {
    it('shows empty history state', async () => {
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('Bạn chưa tải tài liệu nào.')).toBeInTheDocument()
      })
    })

    it('shows history items when available', async () => {
      const historyWithItems = {
        items: [{ ...mockDocument }],
        total: 1,
      }
      setupFetch({
        '/api/documents?limit=10&offset=0': () => makeFetchResponse(historyWithItems),
      })
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('test.pdf')).toBeInTheDocument()
      })
    })

    it('shows "Xem thêm" when there are more items', async () => {
      const historyWithMore = {
        items: [mockDocument],
        total: 15,
      }
      setupFetch({
        '/api/documents?limit=10&offset=0': () => makeFetchResponse(historyWithMore),
      })
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('Xem thêm')).toBeInTheDocument()
      })
    })
  })

  describe('status display', () => {
    it('renders status labels correctly', async () => {
      const historyWithItems = {
        items: [{ ...mockDocument, status: 'ocr_complete' }],
        total: 1,
      }
      setupFetch({
        '/api/documents?limit=10&offset=0': () => makeFetchResponse(historyWithItems),
      })
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('OCR hoàn tất')).toBeInTheDocument()
      })
    })
  })

  describe('API error handling', () => {
    it('shows error when /me fails with network error', async () => {
      setupFetch({
        '/api/auth/me': () => { throw new Error('Network error') },
      })
      render(<App />)
      // Should fall through to login form
      await waitFor(() => {
        expect(screen.getByText('Chào mừng trở lại.')).toBeInTheDocument()
      })
    })

    it('shows error message on login failure', async () => {
      setupFetch({
        '/api/auth/me': () => makeFetchResponse({ detail: 'Unauthorized' }, false, 401),
        '/api/auth/login': () => makeFetchResponse({ detail: 'Sai mật khẩu' }, false, 401),
      })
      render(<App />)
      await waitFor(() => {
        expect(screen.getByLabelText('Tên đăng nhập')).toBeInTheDocument()
      })

      fireEvent.change(screen.getByLabelText('Tên đăng nhập'), { target: { value: 'testuser' } })
      fireEvent.change(screen.getByLabelText('Mật khẩu'), { target: { value: 'wrongpassword' } })
      fireEvent.submit(screen.getByLabelText('Mật khẩu').closest('form'))

      await waitFor(() => {
        expect(screen.getByText('Sai mật khẩu')).toBeInTheDocument()
      })
    })
  })

  describe('logout', () => {
    it('returns to login form after logout', async () => {
      setupFetch({
        '/api/auth/logout': () => makeFetchResponse({}),
      })
      render(<App />)
      await waitFor(() => {
        expect(screen.getByText('testuser')).toBeInTheDocument()
      })
      fireEvent.click(screen.getByText('Đăng xuất'))
      await waitFor(() => {
        expect(screen.getByText('Chào mừng trở lại.')).toBeInTheDocument()
      })
    })
  })
})
