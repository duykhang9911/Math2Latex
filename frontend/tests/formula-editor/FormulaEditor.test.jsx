import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FormulaEditor } from '../../src/components/FormulaEditor'

// MathLive registers <math-field> as a custom element.
// In jsdom it is an unknown element — we mock it as a plain <div>.
beforeEach(() => {
  // Stub MathLive custom element so React can render it
  if (!customElements.get('math-field')) {
    customElements.define('math-field', class extends HTMLElement {
      get value() { return this.getAttribute('value') || '' }
      set value(v) { this.setAttribute('value', v) }
    })
  }
})

const baseFormula = {
  formula_id: 'f-1',
  page_number: 1,
  status: 'ocr_complete',
  confidence: 0.92,
  latex_raw: '\\frac{a}{b}',
  latex_final: null,
  bounds: { x_min: 10, y_min: 20, x_max: 100, y_max: 80 },
  image_url: '/api/documents/d-1/formulas/f-1/image',
}

const defaultProps = {
  formula: baseFormula,
  index: 0,
  selected: false,
  value: '\\frac{a}{b}',
  editable: true,
  onSelect: vi.fn(),
  onChange: vi.fn(),
  onSave: vi.fn(),
  onDelete: vi.fn(),
  onUpdateRegion: vi.fn(),
  coordinates: '10,20,100,80',
  setCoordinates: vi.fn(),
  canEditRegion: false,
}

describe('FormulaEditor', () => {
  // --- S4-02: LaTeX ↔ MathLive ---

  describe('render & display', () => {
    it('renders formula index and page info', () => {
      render(<FormulaEditor {...defaultProps} />)
      expect(screen.getByText('F01')).toBeInTheDocument()
      expect(screen.getByText(/Trang 1/)).toBeInTheDocument()
    })

    it('shows confidence percentage', () => {
      render(<FormulaEditor {...defaultProps} />)
      expect(screen.getByText('92%')).toBeInTheDocument()
    })

    it('shows crop image with correct src', () => {
      render(<FormulaEditor {...defaultProps} />)
      const img = screen.getByAltText('Công thức trang 1')
      expect(img).toBeInTheDocument()
      expect(img.getAttribute('src')).toContain('/api/documents/d-1/formulas/f-1/image')
    })

    it('shows selected class when selected=true', () => {
      const { container } = render(<FormulaEditor {...defaultProps} selected={true} />)
      expect(container.querySelector('.formula-selected')).toBeInTheDocument()
    })
  })

  describe('editable mode — LaTeX textarea', () => {
    it('renders textarea with LaTeX value (fraction)', () => {
      render(<FormulaEditor {...defaultProps} value={'\\frac{a}{b}'} />)
      const textarea = screen.getByLabelText('LaTeX')
      expect(textarea.value).toBe('\\frac{a}{b}')
    })

    it('fires onChange when textarea is edited', () => {
      const onChange = vi.fn()
      render(<FormulaEditor {...defaultProps} onChange={onChange} />)
      const textarea = screen.getByLabelText('LaTeX')
      fireEvent.change(textarea, { target: { value: '\\sqrt{x}' } })
      expect(onChange).toHaveBeenCalledWith('\\sqrt{x}')
    })

    it('renders textarea with square root', () => {
      const val = String.raw`\sqrt{x+1}`
      render(<FormulaEditor {...defaultProps} value={val} />)
      expect(screen.getByLabelText('LaTeX').value).toBe(val)
    })

    it('renders textarea with matrix', () => {
      const matrix = String.raw`\begin{pmatrix} a & b \\ c & d \end{pmatrix}`
      render(<FormulaEditor {...defaultProps} value={matrix} />)
      expect(screen.getByLabelText('LaTeX').value).toBe(matrix)
    })

    it('renders textarea with Greek letters', () => {
      const val = String.raw`\alpha + \beta = \gamma`
      render(<FormulaEditor {...defaultProps} value={val} />)
      expect(screen.getByLabelText('LaTeX').value).toBe(val)
    })

    it('allows bad LaTeX syntax in textarea without crashing', () => {
      // Bad LaTeX (unclosed brace) should not crash the component
      const val = String.raw`\frac{a{b}`
      render(<FormulaEditor {...defaultProps} value={val} />)
      expect(screen.getByLabelText('LaTeX').value).toBe(val)
    })

    it('handles empty LaTeX string', () => {
      render(<FormulaEditor {...defaultProps} value="" />)
      expect(screen.getByLabelText('LaTeX').value).toBe('')
    })
  })

  describe('editable mode — MathLive field', () => {
    it('renders a math-field element', () => {
      const { container } = render(<FormulaEditor {...defaultProps} />)
      const mathField = container.querySelector('math-field')
      expect(mathField).toBeInTheDocument()
    })

    it('math-field has virtual-keyboard-mode="manual"', () => {
      const { container } = render(<FormulaEditor {...defaultProps} />)
      const mathField = container.querySelector('math-field')
      expect(mathField.getAttribute('virtual-keyboard-mode')).toBe('manual')
    })
  })

  describe('submit button', () => {
    it('renders Submit button', () => {
      render(<FormulaEditor {...defaultProps} />)
      expect(screen.getByText(/Submit/)).toBeInTheDocument()
    })

    it('calls onSave when Submit is clicked', () => {
      const onSave = vi.fn()
      render(<FormulaEditor {...defaultProps} onSave={onSave} />)
      fireEvent.click(screen.getByText(/Submit/))
      expect(onSave).toHaveBeenCalledOnce()
    })

    it('shows "Đã lưu" for submitted formulas', () => {
      const formula = { ...baseFormula, status: 'submitted' }
      render(<FormulaEditor {...defaultProps} formula={formula} />)
      expect(screen.getByText('Đã lưu')).toBeInTheDocument()
    })

    it('shows "Chưa gửi" for non-submitted formulas', () => {
      render(<FormulaEditor {...defaultProps} />)
      expect(screen.getByText('Chưa gửi')).toBeInTheDocument()
    })
  })

  describe('OCR raw display', () => {
    it('renders OCR raw in details/summary', () => {
      render(<FormulaEditor {...defaultProps} />)
      expect(screen.getByText('OCR gốc')).toBeInTheDocument()
      // latex_raw also appears in textarea, so use getAllByText
      const codeElements = screen.getAllByText(String.raw`\frac{a}{b}`)
      expect(codeElements.length).toBeGreaterThanOrEqual(2) // textarea + code
      const codeEl = codeElements.find(el => el.tagName === 'CODE')
      expect(codeEl).toBeTruthy()
    })

    it('does not render OCR raw when latex_raw is null', () => {
      const formula = { ...baseFormula, latex_raw: null }
      render(<FormulaEditor {...defaultProps} formula={formula} />)
      expect(screen.queryByText('OCR gốc')).not.toBeInTheDocument()
    })
  })

  describe('non-editable states', () => {
    it('shows "Chờ xác nhận vùng OCR" for proposed status', () => {
      const formula = { ...baseFormula, status: 'proposed' }
      render(<FormulaEditor {...defaultProps} formula={formula} editable={false} />)
      expect(screen.getByText('Chờ xác nhận vùng OCR')).toBeInTheDocument()
    })

    it('shows "Đang chờ OCR" for ocr_queued status', () => {
      const formula = { ...baseFormula, status: 'ocr_queued' }
      render(<FormulaEditor {...defaultProps} formula={formula} editable={false} />)
      expect(screen.getByText('Đang chờ OCR')).toBeInTheDocument()
    })

    it('shows "OCR lỗi" for ocr_failed status', () => {
      const formula = { ...baseFormula, status: 'ocr_failed' }
      render(<FormulaEditor {...defaultProps} formula={formula} editable={false} />)
      expect(screen.getByText(/OCR lỗi/)).toBeInTheDocument()
    })

    it('does not show textarea when not editable', () => {
      render(<FormulaEditor {...defaultProps} editable={false} formula={{ ...baseFormula, status: 'proposed' }} />)
      expect(screen.queryByLabelText('LaTeX')).not.toBeInTheDocument()
    })
  })

  describe('region editing', () => {
    it('shows region edit row when canEditRegion is true', () => {
      const formula = { ...baseFormula, status: 'proposed' }
      render(<FormulaEditor {...defaultProps} formula={formula} canEditRegion={true} />)
      expect(screen.getByLabelText('Tọa độ vùng công thức')).toBeInTheDocument()
    })

    it('does not show region edit when canEditRegion is false', () => {
      render(<FormulaEditor {...defaultProps} canEditRegion={false} />)
      expect(screen.queryByLabelText('Tọa độ vùng công thức')).not.toBeInTheDocument()
    })

    it('calls onUpdateRegion when check button clicked', () => {
      const onUpdateRegion = vi.fn()
      const formula = { ...baseFormula, status: 'proposed' }
      render(<FormulaEditor {...defaultProps} formula={formula} canEditRegion={true} onUpdateRegion={onUpdateRegion} />)
      fireEvent.click(screen.getByTitle('Cập nhật vùng'))
      expect(onUpdateRegion).toHaveBeenCalledOnce()
    })

    it('calls onDelete when delete button clicked', () => {
      const onDelete = vi.fn()
      const formula = { ...baseFormula, status: 'proposed' }
      render(<FormulaEditor {...defaultProps} formula={formula} canEditRegion={true} onDelete={onDelete} />)
      fireEvent.click(screen.getByTitle('Xóa vùng'))
      expect(onDelete).toHaveBeenCalledOnce()
    })
  })
})
