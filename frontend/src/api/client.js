export const API_ORIGIN = `${window.location.protocol}//${window.location.hostname}:8000`
export const API = `${API_ORIGIN}/api/documents`
export const AUTH_API = `${API_ORIGIN}/api/auth`
export const PROCESSING_STATES = new Set(['processing_pages', 'detecting_formulas', 'ocr_processing'])

/**
 * Friendly Vietnamese messages for common HTTP error statuses.
 * Used by handleApiError to display user-readable error messages.
 */
const ERROR_MESSAGES = {
  400: 'Yêu cầu không hợp lệ.',
  401: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
  403: 'Bạn không có quyền thực hiện thao tác này.',
  413: 'File quá lớn. Vui lòng chọn file nhỏ hơn.',
  422: 'Dữ liệu không hợp lệ. Vui lòng kiểm tra lại.',
  429: 'Bạn đã gửi quá nhiều yêu cầu. Vui lòng đợi một lát rồi thử lại.',
  500: 'Lỗi máy chủ. Vui lòng thử lại sau.',
  502: 'Máy chủ tạm thời không phản hồi. Vui lòng thử lại sau.',
  503: 'Hệ thống đang bận. Vui lòng thử lại sau.',
}

/**
 * Callback set by App to handle session expiry (auto logout).
 * @type {(() => void) | null}
 */
let onSessionExpired = null

/**
 * Register a callback that is called when the server returns 401.
 * App.jsx sets this on mount so apiFetch can auto-logout the user.
 */
export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler
}

export const apiFetch = async (url, options = {}) => {
  const response = await fetch(url, { ...options, credentials: 'include' })

  // Auto-logout on 401 (session expired), except for auth endpoints
  if (response.status === 401 && onSessionExpired && !url.includes('/api/auth/')) {
    onSessionExpired()
  }

  return response
}

/**
 * Extract a user-friendly error message from a failed API response.
 * Falls back to the response detail or a generic status message.
 */
export async function extractApiError(response, fallback = 'Thao tác thất bại.') {
  const statusMessage = ERROR_MESSAGES[response.status]
  try {
    const data = await response.json()
    return data.detail || statusMessage || fallback
  } catch {
    return statusMessage || fallback
  }
}

export const HISTORY_PAGE_SIZE = 10

export const formatBytes = (bytes) => {
  if (bytes == null) return '—'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export const formatDate = (value) => (value ? new Date(value).toLocaleString('vi-VN') : '—')

export const fetchHistoryPage = async (offset) => {
  const response = await apiFetch(`${API}?limit=${HISTORY_PAGE_SIZE}&offset=${offset}`)
  if (!response.ok) {
    const msg = await extractApiError(response, 'Không tải được lịch sử')
    throw new Error(msg)
  }
  return response.json()
}

export const downloadFile = async (url, filename) => {
  const response = await apiFetch(url)
  if (!response.ok) {
    const msg = await extractApiError(response, 'Không tải được file')
    throw new Error(msg)
  }
  const objectUrl = URL.createObjectURL(await response.blob())
  const link = window.document.createElement('a')
  link.href = objectUrl
  link.download = filename
  link.click()
  URL.revokeObjectURL(objectUrl)
}

export const STATUS_LABELS = {
  processing_pages: 'Đang tách trang',
  detecting_formulas: 'Đang tìm công thức',
  formula_proposals_ready: 'Chờ xác nhận vùng',
  ocr_processing: 'Đang nhận dạng LaTeX',
  ocr_complete: 'OCR hoàn tất',
  ocr_completed_with_errors: 'OCR có công thức lỗi',
  processing_failed: 'Xử lý thất bại',
  uploaded: 'Đã tải lên',
}
