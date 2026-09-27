import { useEffect, useRef, useState } from 'react'
import { MathfieldElement } from 'mathlive'
import './App.css'

MathfieldElement.fontsDirectory = '/mathlive-fonts/'

const API = 'http://localhost:8000/api/documents'
const PROCESSING_STATES = new Set(['processing_pages', 'detecting_formulas', 'ocr_processing'])

const STATUS_LABELS = {
  processing_pages: 'Đang tách trang',
  detecting_formulas: 'Đang tìm công thức',
  formula_proposals_ready: 'Chờ xác nhận vùng',
  ocr_processing: 'Đang nhận dạng LaTeX',
  ocr_complete: 'OCR hoàn tất',
  ocr_completed_with_errors: 'OCR có công thức lỗi',
  processing_failed: 'Xử lý thất bại',
  uploaded: 'Đã tải lên',
}

function App() {
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

  const refreshDocument = async (documentId) => {
    const [pagesResponse, formulasResponse] = await Promise.all([
      fetch(`${API}/${documentId}/pages`),
      fetch(`${API}/${documentId}/formulas`),
    ])
    const pagesData = await pagesResponse.json()
    const formulasData = await formulasResponse.json()
    if (!pagesResponse.ok) throw new Error(pagesData.detail || 'Không tải được danh sách trang')
    if (!formulasResponse.ok) throw new Error(formulasData.detail || 'Không tải được công thức')

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
  }

  useEffect(() => {
    if (!documentInfo?.document_id || !PROCESSING_STATES.has(documentInfo.status)) return undefined
    const timer = window.setInterval(() => {
      refreshDocument(documentInfo.document_id).catch((error) => setMessage(error.message))
    }, 1600)
    return () => window.clearInterval(timer)
  }, [documentInfo?.document_id, documentInfo?.status])

  const handleUpload = async (event) => {
    event.preventDefault()
    if (!selectedFile) return
    setBusy(true)
    setMessage('')
    const formData = new FormData()
    formData.append('file', selectedFile)
    try {
      const response = await fetch(`${API}/upload`, { method: 'POST', body: formData })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Upload thất bại')
      setDocumentInfo(data)
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
      const response = await fetch(`${API}/${documentInfo.document_id}/formulas/recognize`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Không thể bắt đầu OCR')
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
      const response = await fetch(`${API}/${documentInfo.document_id}/formulas/retry`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Không thể chạy lại OCR')
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
    const response = await fetch(`${API}/${documentInfo.document_id}/formulas/${formula.formula_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x_min: xMin, y_min: yMin, x_max: xMax, y_max: yMax }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Không cập nhật được vùng')
    await refreshDocument(documentInfo.document_id)
  }

  const persistRegionBounds = async (formulaId, bounds) => {
    const response = await fetch(`${API}/${documentInfo.document_id}/formulas/${formulaId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bounds),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Không cập nhật được vùng')
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
    const response = await fetch(`${API}/${documentInfo.document_id}/formulas/${formulaId}`, { method: 'DELETE' })
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Không xóa được vùng')
    }
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
    const response = await fetch(`${API}/${documentInfo.document_id}/formulas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page_number: page.page_number, x_min: xMin, y_min: yMin, x_max: xMax, y_max: yMax }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Không thêm được vùng')
    setManualRegions((current) => ({ ...current, [`page-${page.page_number}`]: '' }))
    await refreshDocument(documentInfo.document_id)
  }

  const submitFormula = async (formula) => {
    const response = await fetch(`${API}/${documentInfo.document_id}/formulas/${formula.formula_id}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latex_final: edits[formula.formula_id] ?? '' }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Không lưu được LaTeX')
    setFormulas((current) => current.map((item) => item.formula_id === formula.formula_id ? { ...item, status: data.status, latex_raw: data.latex_raw, latex_final: data.latex_final } : item))
    setMessage('Đã lưu LaTeX cuối cùng cho công thức.')
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

  return (
    <main className="workspace">
      <header className="topbar">
        <a className="brand" href="#top"><span className="brand-mark">M</span> Math2Latex</a>
        <span className="topbar-note">PDF WORKSPACE <i /></span>
      </header>

      <section className="intro" id="top">
        <div>
          <p className="eyebrow">Formula extraction / 01</p>
          <h1>From PDF to <em>Latex.</em></h1>
          <p className="intro-copy">Chuyển đổi công thức toán học từ PDF sang LaTeX.</p>
        </div>
        <form className="upload-form" onSubmit={handleUpload}>
          <label className="file-picker">
            <input type="file" accept="application/pdf,.pdf" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
            <span className="file-icon" aria-hidden="true">↥</span>
            <span className="file-name">{selectedFile?.name || 'Chọn PDF để bắt đầu'}</span>
            <span className="file-browse">Browse</span>
          </label>
          <button className="primary-button" type="submit" disabled={!selectedFile || busy}>
            {busy ? 'Đang xử lý' : 'Tải PDF'} <span aria-hidden="true">→</span>
          </button>
        </form>
      </section>

      {message && <div className="notice" role="status">{message}</div>}

      {documentInfo && (
        <section className="document-workspace">
          <div className="document-heading">
            <div>
              <p className="eyebrow">Current document</p>
              <h2>{selectedFile?.name || documentInfo.filename || 'Tài liệu PDF'}</h2>
              <span className="document-id">{documentInfo.document_id}</span>
            </div>
            <div className={`status-pill status-${documentInfo.status}`}>
              <span className="status-dot" />{STATUS_LABELS[documentInfo.status] || documentInfo.status}
            </div>
          </div>

          {pages.length > 0 && (
            <div className="review-layout">
              <section className="page-column">
                <div className="section-heading">
                  <div><p className="eyebrow">Document pages</p><h3>Trang PDF</h3></div>
                  <span className="count-label">{pages.length} trang</span>
                </div>
                <div className="page-stack">
                  {pages.map((page) => {
                    const pageFormulas = formulas.filter((formula) => formula.page_number === page.page_number)
                    return (
                      <article className="page-sheet" key={page.page_number}>
                        <div className="page-caption"><span>Trang {String(page.page_number).padStart(2, '0')}</span><span>{pageFormulas.length} vùng</span></div>
                        <div
                          className="page-image-wrap"
                          onPointerMove={(event) => moveRegionPointer(event, page)}
                          onPointerUp={finishRegionPointer}
                          onPointerCancel={finishRegionPointer}
                        >
                          <img src={`http://localhost:8000${page.image_url}`} alt={`Trang ${page.page_number}`} />
                          {pageFormulas.map((formula) => {
                            const bounds = regionDrafts[formula.formula_id] || formula.bounds
                            const canDrag = formula.status === 'proposed' && documentInfo.status === 'formula_proposals_ready'
                            return (
                              <button
                                className={`region-box ${selectedFormulaId === formula.formula_id ? 'is-selected' : ''} ${canDrag ? 'is-draggable' : ''}`}
                                key={formula.formula_id}
                                style={{ left: `${bounds.x_min / page.width * 100}%`, top: `${bounds.y_min / page.height * 100}%`, width: `${(bounds.x_max - bounds.x_min) / page.width * 100}%`, height: `${(bounds.y_max - bounds.y_min) / page.height * 100}%` }}
                                onPointerDown={(event) => startRegionDrag(event, formula, page)}
                                onKeyDown={(event) => nudgeRegionWithKeyboard(event, formula, page)}
                                onClick={() => setSelectedFormulaId(formula.formula_id)}
                                aria-label={`Chọn vùng công thức trang ${page.page_number}`}
                                aria-describedby={canDrag ? `region-help-${formula.formula_id}` : undefined}
                                aria-keyshortcuts="ArrowLeft ArrowRight ArrowUp ArrowDown Alt+ArrowLeft Alt+ArrowRight Alt+ArrowUp Alt+ArrowDown"
                                title={canDrag ? 'Kéo để di chuyển vùng' : `Độ tin cậy ${Math.round((formula.confidence || 0) * 100)}%`}
                              >
                                {canDrag && ['nw', 'ne', 'sw', 'se'].map((corner) => (
                                  <span
                                    aria-label={`Đổi kích thước ${corner}`}
                                    className={`region-handle handle-${corner}`}
                                    key={corner}
                                    onPointerDown={(event) => startRegionDrag(event, formula, page, 'resize', corner)}
                                  />
                                ))}
                              </button>
                            )
                          })}
                          {pageFormulas.filter((formula) => formula.status === 'proposed').map((formula) => (
                            <span className="visually-hidden" id={`region-help-${formula.formula_id}`} key={`help-${formula.formula_id}`}>
                              Dùng phím mũi tên để di chuyển vùng; Alt cộng phím mũi tên để đổi kích thước; giữ Shift để thay đổi 10 pixel.
                            </span>
                          ))}
                        </div>
                        {documentInfo.status === 'formula_proposals_ready' && (
                          <div className="region-tools">
                            <input aria-label={`Tọa độ vùng mới trang ${page.page_number}`} placeholder="x_min,y_min,x_max,y_max" value={manualRegions[`page-${page.page_number}`] || ''} onChange={(event) => setManualRegions((current) => ({ ...current, [`page-${page.page_number}`]: event.target.value }))} />
                            <button className="text-button" onClick={() => perform(() => addRegion(page))}>+ Thêm vùng</button>
                          </div>
                        )}
                      </article>
                    )
                  })}
                </div>
              </section>

              <aside className="formula-column">
                <div className="section-heading formula-heading">
                  <div><p className="eyebrow">Detected expressions</p><h3>Công thức</h3></div>
                  <span className="count-label">{formulas.length} mục</span>
                </div>
                {documentInfo.status === 'formula_proposals_ready' && (
                  <div className="confirm-panel">
                    <p>{proposalCount} vùng đề xuất cần nhận dạng.</p>
                    <button className="dark-button" onClick={runOcr} disabled={busy || !formulas.length}>Xác nhận vùng & chạy OCR <span>→</span></button>
                  </div>
                )}
                {documentInfo.status === 'ocr_completed_with_errors' && failedCount > 0 && (
                  <div className="confirm-panel retry-panel">
                    <p>{failedCount} công thức OCR lỗi.</p>
                    <button className="dark-button" onClick={retryOcr} disabled={busy}>Thử OCR lại <span>↻</span></button>
                  </div>
                )}
                {formulas.length === 0 && <p className="empty-state">Chưa phát hiện công thức trên các trang này.</p>}
                <div className="formula-list">
                  {formulas.map((formula, index) => (
                    <FormulaEditor
                      key={formula.formula_id}
                      formula={formula}
                      index={index}
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
              </aside>
            </div>
          )}
        </section>
      )}
    </main>
  )
}

function FormulaEditor({ formula, index, selected, value, editable, onSelect, onChange, onSave, onDelete, onUpdateRegion, coordinates, setCoordinates, canEditRegion }) {
  const mathfieldRef = useRef(null)

  useEffect(() => {
    const field = mathfieldRef.current
    if (field && field.value !== value) field.value = value
  }, [value])

  return (
    <article className={`formula-item ${selected ? 'formula-selected' : ''}`} onClick={onSelect}>
      <div className="formula-item-top">
        <span className="formula-index">F{String(index + 1).padStart(2, '0')}</span>
        <span className="formula-page">Trang {formula.page_number} · {formula.status}</span>
        {formula.confidence != null && <span className="confidence">{Math.round(formula.confidence * 100)}%</span>}
      </div>
      <img className="formula-crop" src={`http://localhost:8000${formula.image_url}`} alt={`Công thức trang ${formula.page_number}`} />
      {canEditRegion && (
        <div className="region-edit-row" onClick={(event) => event.stopPropagation()}>
          <input aria-label="Tọa độ vùng công thức" value={coordinates} onChange={(event) => setCoordinates(event.target.value)} />
          <button className="icon-button" title="Cập nhật vùng" onClick={onUpdateRegion}>✓</button>
          <button className="icon-button danger-button" title="Xóa vùng" onClick={onDelete}>×</button>
        </div>
      )}
      {editable ? (
        <div className="editor-fields" onClick={(event) => event.stopPropagation()}>
          <label className="field-label" htmlFor={`latex-${formula.formula_id}`}>LaTeX</label>
          <textarea id={`latex-${formula.formula_id}`} value={value} onChange={(event) => onChange(event.target.value)} spellCheck="false" />
          <label className="field-label">MathLive</label>
          <math-field ref={mathfieldRef} className="mathlive-field" onInput={(event) => onChange(event.currentTarget.value)} virtual-keyboard-mode="manual" />
          <div className="save-row">
            <span className={`saved-state ${formula.status === 'submitted' ? 'is-saved' : ''}`}>{formula.status === 'submitted' ? 'Đã lưu' : 'Chưa gửi'}</span>
            <button className="save-button" onClick={onSave}>Submit <span>↗</span></button>
          </div>
        </div>
      ) : (
        <div className="waiting-label">{formula.status === 'proposed' ? 'Chờ xác nhận vùng OCR' : formula.status === 'ocr_queued' ? 'Đang chờ OCR' : formula.status === 'ocr_failed' ? 'OCR lỗi · cần thử lại' : 'Đang chuẩn bị'}</div>
      )}
      {formula.latex_raw && <details className="raw-result"><summary>OCR gốc</summary><code>{formula.latex_raw}</code></details>}
    </article>
  )
}

export default App