import { useEffect, useState, useCallback } from 'react'
import './App.css'

import {
  API,
  AUTH_API,
  PROCESSING_STATES,
  STATUS_LABELS,
  apiFetch,
  fetchHistoryPage,
  extractApiError,
  setSessionExpiredHandler,
} from './api/client'
import { FormulaEditor } from './components/FormulaEditor'
import { PDFUploader } from './components/PDFUploader'
import { HistoryPanel } from './components/HistoryPanel'
import { RegionOverlay } from './components/RegionOverlay'

function App() {
  const [currentUser, setCurrentUser] = useState(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [authMode, setAuthMode] = useState('login')
  const [authUsername, setAuthUsername] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [documentInfo, setDocumentInfo] = useState(null)
  const [pages, setPages] = useState([])
  const [formulas, setFormulas] = useState([])
  const [edits, setEdits] = useState({})
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [selectedFormulaId, setSelectedFormulaId] = useState(null)
  const [manualRegions, setManualRegions] = useState({})
  const [regionDrafts, setRegionDrafts] = useState({})
  const [regionDrag, setRegionDrag] = useState(null)
  const [history, setHistory] = useState([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)

  // Register auto-logout handler for expired sessions (401)
  const handleSessionExpired = useCallback(() => {
    setCurrentUser(null)
    setDocumentInfo(null)
    setPages([])
    setFormulas([])
    setHistory([])
    setHistoryTotal(0)
    setSelectedFile(null)
    setMessage('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.')
  }, [])

  useEffect(() => {
    setSessionExpiredHandler(handleSessionExpired)
    return () => setSessionExpiredHandler(null)
  }, [handleSessionExpired])

  useEffect(() => {
    apiFetch(`${AUTH_API}/me`)
      .then(async (response) => {
        if (response.ok) setCurrentUser(await response.json())
      })
      .catch(() => {})
      .finally(() => setCheckingSession(false))
  }, [])

  const refreshDocument = async (documentId) => {
    const [pagesResponse, formulasResponse] = await Promise.all([
      apiFetch(`${API}/${documentId}/pages`),
      apiFetch(`${API}/${documentId}/formulas`),
    ])
    if (!pagesResponse.ok) throw new Error(await extractApiError(pagesResponse, 'Không tải được danh sách trang'))
    if (!formulasResponse.ok) throw new Error(await extractApiError(formulasResponse, 'Không tải được công thức'))
    const pagesData = await pagesResponse.json()
    const formulasData = await formulasResponse.json()

    setDocumentInfo((current) => ({ ...current, status: formulasData.status || pagesData.status }))
    setPages(pagesData.pages || [])
    setFormulas(formulasData.formulas || [])
    setEdits((current) => {
      const next = { ...current }
      for (const formula of formulasData.formulas || []) {
        if (!(formula.formula_id in next) && (formula.latex_final != null || formula.latex_raw != null)) {
          next[formula.formula_id] = formula.latex_final ?? formula.latex_raw
        }
      }
      return next
    })
    return pagesData.pages || []
  }

  const loadHistory = async (append = false) => {
    setHistoryLoading(true)
    try {
      const data = await fetchHistoryPage(append ? history.length : 0)
      setHistory((current) => (append ? [...current, ...data.items] : data.items))
      setHistoryTotal(data.total)
    } catch (error) {
      setMessage(error.message || 'Không tải được lịch sử')
    } finally {
      setHistoryLoading(false)
    }
  }

  const resetDocumentView = () => {
    setPages([])
    setFormulas([])
    setEdits({})
    setSelectedFormulaId(null)
    setManualRegions({})
    setRegionDrafts({})
  }

  const openDocument = async (documentId) => {
    setBusy(true)
    setMessage('')
    try {
      const response = await apiFetch(`${API}/${documentId}`)
      if (!response.ok) throw new Error(await extractApiError(response, 'Không mở được tài liệu'))
      const data = await response.json()
      resetDocumentView()
      setDocumentInfo({ document_id: data.document_id, filename: data.filename, status: data.status })
      const loadedPages = await refreshDocument(documentId)
      if (loadedPages.length === 0 && !PROCESSING_STATES.has(data.status) && data.status !== 'processing_failed') {
        setMessage('Không còn ảnh trang của tài liệu này. Bạn vẫn có thể tải PDF gốc hoặc xuất LaTeX đã lưu nếu còn.')
      }
    } catch (error) {
      setMessage(error.message || 'Không mở được tài liệu')
    } finally {
      setBusy(false)
    }
  }

  const deleteHistoryItem = async (item) => {
    if (!window.confirm(`Xóa "${item.filename}" cùng toàn bộ công thức đã lưu? Không thể hoàn tác.`)) return
    const response = await apiFetch(`${API}/${item.document_id}`, { method: 'DELETE' })
    if (!response.ok) throw new Error(await extractApiError(response, 'Không xóa được tài liệu'))
    setMessage('Đã xóa tài liệu khỏi lịch sử.')
    if (documentInfo?.document_id === item.document_id) {
      setDocumentInfo(null)
      resetDocumentView()
    } else {
      await loadHistory()
    }
  }

  useEffect(() => {
    if (!documentInfo?.document_id || !PROCESSING_STATES.has(documentInfo.status)) return undefined
    const timer = window.setInterval(() => {
      refreshDocument(documentInfo.document_id).catch((error) => setMessage(error.message))
    }, 1600)
    return () => window.clearInterval(timer)
  }, [documentInfo?.document_id, documentInfo?.status])

  // Tải lại lịch sử khi đăng nhập và mỗi khi tài liệu đang mở đổi trạng thái (upload, OCR xong...).
  const currentUserId = currentUser?.id
  const openDocumentId = documentInfo?.document_id
  const openDocumentStatus = documentInfo?.status
  useEffect(() => {
    if (!currentUserId) return undefined
    let cancelled = false
    fetchHistoryPage(0)
      .then((data) => {
        if (cancelled) return
        setHistory(data.items)
        setHistoryTotal(data.total)
      })
      .catch((error) => {
        if (!cancelled) setMessage(error.message || 'Không tải được lịch sử')
      })
    return () => { cancelled = true }
  }, [currentUserId, openDocumentId, openDocumentStatus])

  const handleAuth = async (event) => {
    event.preventDefault()
    setBusy(true)
    setMessage('')
    try {
      const response = await apiFetch(`${AUTH_API}/${authMode === 'login' ? 'login' : 'register'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername, password: authPassword }),
      })
      if (!response.ok) {
        const msg = await extractApiError(response, 'Không thể xác thực tài khoản')
        throw new Error(msg)
      }
      const data = await response.json()
      setCurrentUser(data)
      setAuthPassword('')
      setMessage(authMode === 'login' ? 'Đăng nhập thành công.' : 'Tạo tài khoản thành công.')
    } catch (error) {
      setMessage(error.message || 'Không thể kết nối máy chủ.')
    } finally {
      setBusy(false)
    }
  }

  const handleLogout = async () => {
    await apiFetch(`${AUTH_API}/logout`, { method: 'POST' }).catch(() => {})
    setCurrentUser(null)
    setDocumentInfo(null)
    setPages([])
    setFormulas([])
    setHistory([])
    setHistoryTotal(0)
    setSelectedFile(null)
    setMessage('Bạn đã đăng xuất.')
  }

  const handleUpload = async (event) => {
    event.preventDefault()
    if (!selectedFile) return
    setBusy(true)
    setMessage('')
    const formData = new FormData()
    formData.append('file', selectedFile)
    try {
      const response = await apiFetch(`${API}/upload`, { method: 'POST', body: formData })
      if (!response.ok) {
        const msg = await extractApiError(response, 'Upload thất bại')
        throw new Error(msg)
      }
      const data = await response.json()
      setDocumentInfo({ ...data, filename: selectedFile.name })
      setPages([])
      setFormulas([])
      setEdits({})
      setSelectedFormulaId(null)
      setMessage('PDF đã được tải lên. Đang chuẩn bị trang và đề xuất vùng công thức.')
      await refreshDocument(data.document_id)
    } catch (error) {
      setMessage(error.message || 'Có lỗi xảy ra khi tải tài liệu.')
    } finally {
      setBusy(false)
    }
  }

  const runOcr = async () => {
    if (!documentInfo) return
    setBusy(true)
    try {
      const response = await apiFetch(`${API}/${documentInfo.document_id}/formulas/recognize`, { method: 'POST' })
      if (!response.ok) throw new Error(await extractApiError(response, 'Không thể bắt đầu OCR'))
      const data = await response.json()
      setDocumentInfo((current) => ({ ...current, status: data.status }))
      setMessage(`Đã đưa ${data.queued_count} vùng vào hàng xử lý OCR.`)
    } catch (error) {
      setMessage(error.message)
    } finally {
      setBusy(false)
    }
  }

  const retryOcr = async () => {
    if (!documentInfo) return
    setBusy(true)
    try {
      const response = await apiFetch(`${API}/${documentInfo.document_id}/formulas/retry`, { method: 'POST' })
      if (!response.ok) throw new Error(await extractApiError(response, 'Không thể chạy lại OCR'))
      const data = await response.json()
      setDocumentInfo((current) => ({ ...current, status: data.status }))
      setMessage(`Đã đưa ${data.queued_count} công thức lỗi vào hàng OCR lại.`)
    } catch (error) {
      setMessage(error.message)
    } finally {
      setBusy(false)
    }
  }

  const updateRegion = async (formula) => {
    const input = manualRegions[formula.formula_id]
    if (!input) return
    const [xMin, yMin, xMax, yMax] = input.split(',').map(Number)
    if (![xMin, yMin, xMax, yMax].every(Number.isFinite)) {
      setMessage('Nhập tọa độ theo dạng x_min,y_min,x_max,y_max.')
      return
    }
    const response = await apiFetch(`${API}/${documentInfo.document_id}/formulas/${formula.formula_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x_min: xMin, y_min: yMin, x_max: xMax, y_max: yMax }),
    })
    if (!response.ok) throw new Error(await extractApiError(response, 'Không cập nhật được vùng'))
    await refreshDocument(documentInfo.document_id)
  }

  const persistRegionBounds = async (formulaId, bounds) => {
    const response = await apiFetch(`${API}/${documentInfo.document_id}/formulas/${formulaId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bounds),
    })
    if (!response.ok) throw new Error(await extractApiError(response, 'Không cập nhật được vùng'))
    const data = await response.json()
    setFormulas((current) => current.map((formula) => formula.formula_id === formulaId ? { ...formula, bounds: data.bounds, image_url: data.image_url } : formula))
    setRegionDrafts((current) => {
      const next = { ...current }
      delete next[formulaId]
      return next
    })
    setManualRegions((current) => {
      const next = { ...current }
      delete next[formulaId]
      return next
    })
  }

  const startRegionDrag = (event, formula, page, mode = 'move', corner = null) => {
    if (event.button !== 0 || documentInfo.status !== 'formula_proposals_ready') return
    event.preventDefault()
    event.stopPropagation()
    const imageWrap = event.currentTarget.closest('.page-image-wrap')
    const imageRect = imageWrap.getBoundingClientRect()
    imageWrap.setPointerCapture(event.pointerId)
    setRegionDrag({
      pointerId: event.pointerId,
      formulaId: formula.formula_id,
      imageWrap,
      pageWidth: page.width,
      pageHeight: page.height,
      startX: (event.clientX - imageRect.left) * page.width / imageRect.width,
      startY: (event.clientY - imageRect.top) * page.height / imageRect.height,
      original: { ...(regionDrafts[formula.formula_id] || formula.bounds) },
      bounds: { ...(regionDrafts[formula.formula_id] || formula.bounds) },
      mode,
      corner,
    })
    setSelectedFormulaId(formula.formula_id)
  }

  const moveRegionPointer = (event, page) => {
    const drag = regionDrag
    if (!drag || drag.pointerId !== event.pointerId) return
    const imageRect = drag.imageWrap.getBoundingClientRect()
    const pointerX = (event.clientX - imageRect.left) * page.width / imageRect.width
    const pointerY = (event.clientY - imageRect.top) * page.height / imageRect.height
    const deltaX = pointerX - drag.startX
    const deltaY = pointerY - drag.startY
    const bounds = { ...drag.original }

    if (drag.mode === 'move') {
      const width = bounds.x_max - bounds.x_min
      const height = bounds.y_max - bounds.y_min
      bounds.x_min = Math.max(0, Math.min(page.width - width, bounds.x_min + deltaX))
      bounds.y_min = Math.max(0, Math.min(page.height - height, bounds.y_min + deltaY))
      bounds.x_max = bounds.x_min + width
      bounds.y_max = bounds.y_min + height
    } else {
      if (drag.corner.includes('w')) bounds.x_min = Math.max(0, Math.min(bounds.x_max - 10, bounds.x_min + deltaX))
      if (drag.corner.includes('e')) bounds.x_max = Math.min(page.width, Math.max(bounds.x_min + 10, bounds.x_max + deltaX))
      if (drag.corner.includes('n')) bounds.y_min = Math.max(0, Math.min(bounds.y_max - 10, bounds.y_min + deltaY))
      if (drag.corner.includes('s')) bounds.y_max = Math.min(page.height, Math.max(bounds.y_min + 10, bounds.y_max + deltaY))
    }

    const updatedBounds = Object.fromEntries(Object.entries(bounds).map(([key, value]) => [key, Math.round(value)]))
    setRegionDrag({ ...drag, bounds: updatedBounds })
    setRegionDrafts((current) => ({ ...current, [drag.formulaId]: updatedBounds }))
  }

  const finishRegionPointer = async (event) => {
    const drag = regionDrag
    if (!drag || drag.pointerId !== event.pointerId) return
    setRegionDrag(null)
    if (drag.imageWrap.hasPointerCapture(event.pointerId)) drag.imageWrap.releasePointerCapture(event.pointerId)
    if (Object.keys(drag.bounds).some((key) => drag.bounds[key] !== drag.original[key])) {
      await perform(() => persistRegionBounds(drag.formulaId, drag.bounds))
    }
  }

  const nudgeRegionWithKeyboard = (event, formula, page) => {
    const deltas = {
      ArrowLeft: [-1, 0],
      ArrowRight: [1, 0],
      ArrowUp: [0, -1],
      ArrowDown: [0, 1],
    }
    const delta = deltas[event.key]
    if (!delta || formula.status !== 'proposed' || documentInfo.status !== 'formula_proposals_ready') return

    event.preventDefault()
    event.stopPropagation()
    const step = event.shiftKey ? 10 : 1
    const bounds = { ...(regionDrafts[formula.formula_id] || formula.bounds) }
    if (event.altKey) {
      bounds.x_max = Math.max(bounds.x_min + 10, Math.min(page.width, bounds.x_max + delta[0] * step))
      bounds.y_max = Math.max(bounds.y_min + 10, Math.min(page.height, bounds.y_max + delta[1] * step))
    } else {
      const width = bounds.x_max - bounds.x_min
      const height = bounds.y_max - bounds.y_min
      bounds.x_min = Math.max(0, Math.min(page.width - width, bounds.x_min + delta[0] * step))
      bounds.y_min = Math.max(0, Math.min(page.height - height, bounds.y_min + delta[1] * step))
      bounds.x_max = bounds.x_min + width
      bounds.y_max = bounds.y_min + height
    }

    const roundedBounds = Object.fromEntries(Object.entries(bounds).map(([key, value]) => [key, Math.round(value)]))
    setRegionDrafts((current) => ({ ...current, [formula.formula_id]: roundedBounds }))
    setSelectedFormulaId(formula.formula_id)
    perform(() => persistRegionBounds(formula.formula_id, roundedBounds))
  }

  const deleteRegion = async (formulaId) => {
    const response = await apiFetch(`${API}/${documentInfo.document_id}/formulas/${formulaId}`, { method: 'DELETE' })
    if (!response.ok) throw new Error(await extractApiError(response, 'Không xóa được vùng'))
    setFormulas((current) => current.filter((formula) => formula.formula_id !== formulaId))
    setSelectedFormulaId(null)
  }

  const addRegion = async (page) => {
    const input = manualRegions[`page-${page.page_number}`]
    if (!input) return
    const [xMin, yMin, xMax, yMax] = input.split(',').map(Number)
    if (![xMin, yMin, xMax, yMax].every(Number.isFinite)) {
      setMessage('Nhập tọa độ theo dạng x_min,y_min,x_max,y_max.')
      return
    }
    const response = await apiFetch(`${API}/${documentInfo.document_id}/formulas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page_number: page.page_number, x_min: xMin, y_min: yMin, x_max: xMax, y_max: yMax }),
    })
    if (!response.ok) throw new Error(await extractApiError(response, 'Không thêm được vùng'))
    setManualRegions((current) => ({ ...current, [`page-${page.page_number}`]: '' }))
    await refreshDocument(documentInfo.document_id)
  }

  const submitFormula = async (formula) => {
    const response = await apiFetch(`${API}/${documentInfo.document_id}/formulas/${formula.formula_id}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latex_final: edits[formula.formula_id] ?? '' }),
    })
    if (!response.ok) throw new Error(await extractApiError(response, 'Không lưu được LaTeX'))
    const data = await response.json()
    setFormulas((current) => current.map((item) => item.formula_id === formula.formula_id ? { ...item, status: data.status, latex_raw: data.latex_raw, latex_final: data.latex_final } : item))
    setMessage('Đã lưu LaTeX cuối cùng cho công thức.')
    await loadHistory()
  }

  const perform = async (callback) => {
    setMessage('')
    try {
      await callback()
    } catch (error) {
      setMessage(error.message || 'Thao tác thất bại.')
    }
  }

  const proposalCount = formulas.filter((formula) => formula.status === 'proposed').length
  const failedCount = formulas.filter((formula) => formula.status === 'ocr_failed').length

  if (checkingSession) {
    return <main className="auth-shell"><p className="eyebrow">Math2Latex</p><p className="auth-loading">Đang kiểm tra phiên đăng nhập…</p></main>
  }

  if (!currentUser) {
    return (
      <main className="auth-shell">
        <section className="auth-panel">
          <a className="brand" href="#top"><span className="brand-mark">M</span> Math2Latex</a>
          <p className="eyebrow auth-eyebrow">PDF formula workspace</p>
          <h1>{authMode === 'login' ? 'Chào mừng trở lại.' : 'Tạo tài khoản.'}</h1>
          <p className="auth-copy">Đăng nhập để quản lý PDF và các công thức LaTeX của bạn.</p>
          <form className="auth-form" onSubmit={handleAuth}>
            <label htmlFor="auth-username">Tên đăng nhập</label>
            <input id="auth-username" autoComplete="username" minLength={3} maxLength={32} pattern="[A-Za-z0-9._-]+" value={authUsername} onChange={(event) => setAuthUsername(event.target.value)} required />
            <label htmlFor="auth-password">Mật khẩu</label>
            <input id="auth-password" type="password" autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength={8} maxLength={128} value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} required />
            <button className="primary-button auth-submit" type="submit" disabled={busy}>
              {busy ? 'Đang xử lý…' : authMode === 'login' ? 'Đăng nhập' : 'Đăng ký'} <span aria-hidden="true">→</span>
            </button>
          </form>
          {message && <p className="auth-message" role="status">{message}</p>}
          <p className="auth-switch">
            {authMode === 'login' ? 'Chưa có tài khoản?' : 'Đã có tài khoản?'}{' '}
            <button type="button" className="text-button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setMessage('') }}>
              {authMode === 'login' ? 'Đăng ký' : 'Đăng nhập'}
            </button>
          </p>
        </section>
      </main>
    )
  }

  return (
    <main className="workspace">
      <header className="topbar">
        <a className="brand" href="#top"><span className="brand-mark">M</span> Math2Latex</a>
        <div className="account-actions">
          <span className="account-name">{currentUser.username}</span>
          <button type="button" className="logout-button" onClick={handleLogout}>Đăng xuất</button>
        </div>
      </header>

      <section className="intro" id="top">
        <div>
          <p className="eyebrow">Formula extraction / 01</p>
          <h1>From PDF to <em>Latex.</em></h1>
          <p className="intro-copy">Chuyển đổi công thức toán học từ PDF sang LaTeX.</p>
        </div>
        <PDFUploader selectedFile={selectedFile} setSelectedFile={setSelectedFile} busy={busy} onUpload={handleUpload} />
      </section>

      {message && <div className="notice" role="status">{message}</div>}

      <HistoryPanel
        history={history}
        historyTotal={historyTotal}
        historyLoading={historyLoading}
        documentInfo={documentInfo}
        busy={busy}
        onOpen={openDocument}
        onDelete={deleteHistoryItem}
        onLoadMore={() => loadHistory(true)}
        onPerform={perform}
      />

      {documentInfo && (
        <section className="document-workspace">
          <div className="document-heading">
            <div>
              <p className="eyebrow">Current document</p>
              <h2>{documentInfo.filename || selectedFile?.name || 'Tài liệu PDF'}</h2>
              <span className="document-id">{documentInfo.document_id}</span>
            </div>
            <div className={`status-pill status-${documentInfo.status}`}>
              <span className="status-dot" />{STATUS_LABELS[documentInfo.status] || documentInfo.status}
            </div>
          </div>

          {pages.length > 0 && (
            <div className="review-pages">
              <div className="review-toolbar">
                <div className="section-heading">
                  <div><p className="eyebrow">Document pages</p><h3>Theo dõi từng trang</h3></div>
                  <span className="count-label">{pages.length} trang · {formulas.length} công thức</span>
                </div>
                {documentInfo.status === 'formula_proposals_ready' && (
                  <div className="confirm-panel">
                    <p>{proposalCount} vùng đề xuất cần nhận dạng.</p>
                    <button className="dark-button" onClick={runOcr} disabled={busy || !formulas.length}>Xác nhận vùng &amp; chạy OCR <span>→</span></button>
                  </div>
                )}
                {documentInfo.status === 'ocr_completed_with_errors' && failedCount > 0 && (
                  <div className="confirm-panel retry-panel">
                    <p>{failedCount} công thức OCR lỗi.</p>
                    <button className="dark-button" onClick={retryOcr} disabled={busy}>Thử OCR lại <span>↻</span></button>
                  </div>
                )}
              </div>

              {pages.map((page) => {
                const pageFormulas = formulas.filter((formula) => formula.page_number === page.page_number)
                const submittedOnPage = pageFormulas.filter((formula) => formula.status === 'submitted').length
                return (
                  <section className="page-review" id={`page-${page.page_number}`} key={page.page_number} aria-labelledby={`page-title-${page.page_number}`}>
                    <div className="page-review-heading">
                      <h3 id={`page-title-${page.page_number}`}>Trang {String(page.page_number).padStart(2, '0')}</h3>
                      <span className="count-label">{pageFormulas.length} vùng · {submittedOnPage} đã lưu</span>
                    </div>
                    <div className="page-review-body">
                      <article className="page-sheet">
                        <RegionOverlay
                          page={page}
                          pageFormulas={pageFormulas}
                          documentInfo={documentInfo}
                          regionDrafts={regionDrafts}
                          selectedFormulaId={selectedFormulaId}
                          onPointerMove={(event) => moveRegionPointer(event, page)}
                          onPointerUp={finishRegionPointer}
                          onPointerCancel={finishRegionPointer}
                          onPointerDown={startRegionDrag}
                          onKeyDown={nudgeRegionWithKeyboard}
                          onSelect={setSelectedFormulaId}
                        />
                        {documentInfo.status === 'formula_proposals_ready' && (
                          <div className="region-tools">
                            <input aria-label={`Tọa độ vùng mới trang ${page.page_number}`} placeholder="x_min,y_min,x_max,y_max" value={manualRegions[`page-${page.page_number}`] || ''} onChange={(event) => setManualRegions((current) => ({ ...current, [`page-${page.page_number}`]: event.target.value }))} />
                            <button className="text-button" onClick={() => perform(() => addRegion(page))}>+ Thêm vùng</button>
                          </div>
                        )}
                      </article>

                      <div className="page-formulas">
                        {pageFormulas.length === 0 && <p className="empty-state">Trang này chưa có vùng công thức.</p>}
                        <div className="formula-list">
                          {pageFormulas.map((formula) => (
                            <FormulaEditor
                              key={formula.formula_id}
                              formula={formula}
                              index={formulas.indexOf(formula)}
                              selected={selectedFormulaId === formula.formula_id}
                              value={edits[formula.formula_id] ?? ''}
                              editable={formula.status === 'ocr_complete' || formula.status === 'submitted'}
                              onSelect={() => setSelectedFormulaId(formula.formula_id)}
                              onChange={(value) => setEdits((current) => ({ ...current, [formula.formula_id]: value }))}
                              onSave={() => perform(() => submitFormula(formula))}
                              onDelete={() => perform(() => deleteRegion(formula.formula_id))}
                              onUpdateRegion={() => perform(() => updateRegion(formula))}
                              coordinates={manualRegions[formula.formula_id] ?? `${formula.bounds.x_min},${formula.bounds.y_min},${formula.bounds.x_max},${formula.bounds.y_max}`}
                              setCoordinates={(value) => setManualRegions((current) => ({ ...current, [formula.formula_id]: value }))}
                              canEditRegion={formula.status === 'proposed'}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  </section>
                )
              })}
            </div>
          )}
        </section>
      )}
    </main>
  )
}

export default App
