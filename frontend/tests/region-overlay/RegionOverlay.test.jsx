import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { RegionOverlay } from '../../src/components/RegionOverlay'

const basePage = {
  page_number: 1,
  width: 1000,
  height: 1400,
  image_url: '/api/documents/d-1/pages/1/image',
}

const makeFormula = (overrides = {}) => ({
  formula_id: 'f-1',
  page_number: 1,
  status: 'proposed',
  confidence: 0.95,
  bounds: { x_min: 100, y_min: 200, x_max: 400, y_max: 300 },
  ...overrides,
})

const defaultProps = {
  page: basePage,
  pageFormulas: [makeFormula()],
  documentInfo: { document_id: 'd-1', status: 'formula_proposals_ready' },
  regionDrafts: {},
  selectedFormulaId: null,
  onPointerMove: vi.fn(),
  onPointerUp: vi.fn(),
  onPointerCancel: vi.fn(),
  onPointerDown: vi.fn(),
  onKeyDown: vi.fn(),
  onSelect: vi.fn(),
}

describe('RegionOverlay', () => {
  // --- S4-03: overlay pointer & keyboard tests ---

  describe('render', () => {
    it('renders page image with correct src', () => {
      render(<RegionOverlay {...defaultProps} />)
      const img = screen.getByAltText('Trang 1')
      expect(img).toBeInTheDocument()
      expect(img.getAttribute('src')).toContain('/api/documents/d-1/pages/1/image')
    })

    it('renders one region box per formula', () => {
      const formulas = [makeFormula(), makeFormula({ formula_id: 'f-2', bounds: { x_min: 500, y_min: 600, x_max: 700, y_max: 800 } })]
      const { container } = render(<RegionOverlay {...defaultProps} pageFormulas={formulas} />)
      expect(container.querySelectorAll('.region-box')).toHaveLength(2)
    })

    it('renders no region boxes when pageFormulas is empty', () => {
      const { container } = render(<RegionOverlay {...defaultProps} pageFormulas={[]} />)
      expect(container.querySelectorAll('.region-box')).toHaveLength(0)
    })
  })

  describe('region positioning', () => {
    it('sets percentage-based position from bounds and page dimensions', () => {
      const { container } = render(<RegionOverlay {...defaultProps} />)
      const box = container.querySelector('.region-box')
      // x_min=100/1000=10%, y_min=200/1400≈14.29%, width=(400-100)/1000=30%, height=(300-200)/1400≈7.14%
      expect(box.style.left).toBe('10%')
      expect(box.style.top).toContain('14.')
      expect(box.style.width).toBe('30%')
      expect(box.style.height).toContain('7.')
    })

    it('uses regionDrafts bounds when available', () => {
      const drafts = { 'f-1': { x_min: 200, y_min: 300, x_max: 500, y_max: 400 } }
      const { container } = render(<RegionOverlay {...defaultProps} regionDrafts={drafts} />)
      const box = container.querySelector('.region-box')
      // x_min=200/1000=20%
      expect(box.style.left).toBe('20%')
    })
  })

  describe('draggable state', () => {
    it('has is-draggable class when proposed + formula_proposals_ready', () => {
      const { container } = render(<RegionOverlay {...defaultProps} />)
      expect(container.querySelector('.is-draggable')).toBeInTheDocument()
    })

    it('does NOT have is-draggable when status is not proposed', () => {
      const formulas = [makeFormula({ status: 'ocr_complete' })]
      const { container } = render(<RegionOverlay {...defaultProps} pageFormulas={formulas} />)
      expect(container.querySelector('.is-draggable')).toBeNull()
    })

    it('does NOT have is-draggable when document status is not formula_proposals_ready', () => {
      const { container } = render(<RegionOverlay {...defaultProps} documentInfo={{ document_id: 'd-1', status: 'ocr_processing' }} />)
      expect(container.querySelector('.is-draggable')).toBeNull()
    })
  })

  describe('selection', () => {
    it('adds is-selected class when formula matches selectedFormulaId', () => {
      const { container } = render(<RegionOverlay {...defaultProps} selectedFormulaId="f-1" />)
      expect(container.querySelector('.is-selected')).toBeInTheDocument()
    })

    it('does not have is-selected when no formula matches', () => {
      const { container } = render(<RegionOverlay {...defaultProps} selectedFormulaId="f-999" />)
      expect(container.querySelector('.is-selected')).toBeNull()
    })

    it('calls onSelect when region box is clicked', () => {
      const onSelect = vi.fn()
      const { container } = render(<RegionOverlay {...defaultProps} onSelect={onSelect} />)
      fireEvent.click(container.querySelector('.region-box'))
      expect(onSelect).toHaveBeenCalledWith('f-1')
    })
  })

  describe('resize handles', () => {
    it('renders 4 resize handles for proposed formulas (nw, ne, sw, se)', () => {
      const { container } = render(<RegionOverlay {...defaultProps} />)
      expect(container.querySelector('.handle-nw')).toBeInTheDocument()
      expect(container.querySelector('.handle-ne')).toBeInTheDocument()
      expect(container.querySelector('.handle-sw')).toBeInTheDocument()
      expect(container.querySelector('.handle-se')).toBeInTheDocument()
    })

    it('does NOT render resize handles for non-proposed formulas', () => {
      const formulas = [makeFormula({ status: 'ocr_complete' })]
      const { container } = render(<RegionOverlay {...defaultProps} pageFormulas={formulas} />)
      expect(container.querySelector('.region-handle')).toBeNull()
    })
  })

  describe('pointer events', () => {
    it('calls onPointerDown when region box receives pointerdown', () => {
      const onPointerDown = vi.fn()
      const { container } = render(<RegionOverlay {...defaultProps} onPointerDown={onPointerDown} />)
      fireEvent.pointerDown(container.querySelector('.region-box'))
      expect(onPointerDown).toHaveBeenCalled()
    })

    it('calls onPointerMove on the wrapper div', () => {
      const onPointerMove = vi.fn()
      const { container } = render(<RegionOverlay {...defaultProps} onPointerMove={onPointerMove} />)
      fireEvent.pointerMove(container.querySelector('.page-image-wrap'))
      expect(onPointerMove).toHaveBeenCalled()
    })

    it('calls onPointerUp on the wrapper div', () => {
      const onPointerUp = vi.fn()
      const { container } = render(<RegionOverlay {...defaultProps} onPointerUp={onPointerUp} />)
      fireEvent.pointerUp(container.querySelector('.page-image-wrap'))
      expect(onPointerUp).toHaveBeenCalled()
    })
  })

  describe('keyboard events', () => {
    it('calls onKeyDown when a key is pressed on the region box', () => {
      const onKeyDown = vi.fn()
      const { container } = render(<RegionOverlay {...defaultProps} onKeyDown={onKeyDown} />)
      fireEvent.keyDown(container.querySelector('.region-box'), { key: 'ArrowLeft' })
      expect(onKeyDown).toHaveBeenCalled()
    })
  })

  describe('accessibility', () => {
    it('region box has aria-label for formula selection', () => {
      render(<RegionOverlay {...defaultProps} />)
      expect(screen.getByLabelText('Chọn vùng công thức trang 1')).toBeInTheDocument()
    })

    it('renders keyboard help text for proposed formulas', () => {
      render(<RegionOverlay {...defaultProps} />)
      expect(screen.getByText(/phím mũi tên để di chuyển vùng/)).toBeInTheDocument()
    })

    it('region box has aria-keyshortcuts attribute', () => {
      const { container } = render(<RegionOverlay {...defaultProps} />)
      const box = container.querySelector('.region-box')
      expect(box.getAttribute('aria-keyshortcuts')).toContain('ArrowLeft')
    })
  })
})
