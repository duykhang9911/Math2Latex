import { useRef, useState } from 'react'
import { API_ORIGIN } from '../api/client'
import { useMathfieldSync } from '../hooks/useLatexSync'

export function FormulaEditor({ formula, index, selected, value, editable, onSelect, onChange, onSave, onDelete, onUpdateRegion, coordinates, setCoordinates, canEditRegion }) {
  const mathfieldRef = useRef(null)
  const [mathError, setMathError] = useState(null)

  useMathfieldSync(mathfieldRef, value)

  const handleMathInput = (event) => {
    setMathError(null)
    try {
      onChange(event.currentTarget.value)
    } catch {
      setMathError('MathLive không thể xử lý biểu thức này.')
    }
  }

  const handleTextareaChange = (event) => {
    setMathError(null)
    const newValue = event.target.value
    onChange(newValue)
    // Check if MathLive can handle the new value
    try {
      const field = mathfieldRef.current
      if (field && typeof field.setValue === 'function') {
        field.setValue(newValue)
      } else if (field) {
        field.value = newValue
      }
    } catch {
      setMathError('MathLive không thể hiển thị biểu thức này. Bạn vẫn có thể chỉnh sửa LaTeX thủ công.')
    }
  }

  return (
    <article className={`formula-item ${selected ? 'formula-selected' : ''}`} onClick={onSelect}>
      <div className="formula-item-top">
        <span className="formula-index">F{String(index + 1).padStart(2, '0')}</span>
        <span className="formula-page">Trang {formula.page_number} · {formula.status}</span>
        {formula.confidence != null && <span className="confidence">{Math.round(formula.confidence * 100)}%</span>}
      </div>
      <img className="formula-crop" src={`${API_ORIGIN}${formula.image_url}`} alt={`Công thức trang ${formula.page_number}`} />
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
          <textarea id={`latex-${formula.formula_id}`} value={value} onChange={handleTextareaChange} spellCheck="false" />
          <label className="field-label">MathLive</label>
          <math-field ref={mathfieldRef} className="mathlive-field" onInput={handleMathInput} virtual-keyboard-mode="manual" />
          {mathError && <p className="math-error-warning" role="alert">{mathError}</p>}
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
