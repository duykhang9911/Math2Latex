import { API_ORIGIN } from '../api/client'

export function RegionOverlay({ page, pageFormulas, documentInfo, regionDrafts, selectedFormulaId, onPointerMove, onPointerUp, onPointerCancel, onPointerDown, onKeyDown, onSelect }) {
  return (
    <div
      className="page-image-wrap"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
    >
      <img src={`${API_ORIGIN}${page.image_url}`} alt={`Trang ${page.page_number}`} />
      {pageFormulas.map((formula) => {
        const bounds = regionDrafts[formula.formula_id] || formula.bounds
        const canDrag = formula.status === 'proposed' && documentInfo.status === 'formula_proposals_ready'
        return (
          <button
            className={`region-box ${selectedFormulaId === formula.formula_id ? 'is-selected' : ''} ${canDrag ? 'is-draggable' : ''}`}
            key={formula.formula_id}
            style={{ left: `${bounds.x_min / page.width * 100}%`, top: `${bounds.y_min / page.height * 100}%`, width: `${(bounds.x_max - bounds.x_min) / page.width * 100}%`, height: `${(bounds.y_max - bounds.y_min) / page.height * 100}%` }}
            onPointerDown={(event) => onPointerDown(event, formula, page)}
            onKeyDown={(event) => onKeyDown(event, formula, page)}
            onClick={() => onSelect(formula.formula_id)}
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
                onPointerDown={(event) => onPointerDown(event, formula, page, 'resize', corner)}
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
  )
}
