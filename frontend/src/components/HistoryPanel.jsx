import { API, PROCESSING_STATES, STATUS_LABELS, formatBytes, formatDate, downloadFile } from '../api/client'

export function HistoryPanel({ history, historyTotal, historyLoading, documentInfo, busy, onOpen, onDelete, onLoadMore, onPerform }) {
  return (
    <section className="history-section" aria-labelledby="history-title">
      <div className="section-heading">
        <div><p className="eyebrow">Upload history</p><h3 id="history-title">Lịch sử tải lên</h3></div>
        <span className="count-label">{historyTotal} tài liệu</span>
      </div>
      {history.length === 0 && !historyLoading && <p className="empty-state">Bạn chưa tải tài liệu nào.</p>}
      <ul className="grid gap-2 m-0 mb-2.5 p-0 list-none">
        {history.map((item) => (
          <li className={`grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3.5 border border-line p-2.5 px-3.5 bg-white ${documentInfo?.document_id === item.document_id ? 'border-green' : ''}`} key={item.document_id}>
            <button type="button" className="grid gap-1 border-0 p-0 bg-transparent text-ink text-left cursor-pointer disabled:cursor-wait" onClick={() => onOpen(item.document_id)} disabled={busy}>
              <span className="font-bold break-all">{item.filename}</span>
              <span className="text-muted text-[11px]">
                {formatDate(item.created_at)} · {formatBytes(item.file_size_bytes)} · {item.page_count ?? '—'} trang · {item.submitted_count}/{item.formula_count} công thức đã lưu
              </span>
            </button>
            <div className={`status-pill status-${item.status}`}>
              <span className="status-dot" />{STATUS_LABELS[item.status] || item.status}
            </div>
            <div className="flex gap-2.5">
              <button type="button" className="text-button" onClick={() => onPerform(() => downloadFile(`${API}/${item.document_id}/source`, item.filename))}>Tải PDF</button>
              <button type="button" className="text-button" disabled={item.submitted_count === 0} onClick={() => onPerform(() => downloadFile(`${API}/${item.document_id}/export`, `${item.filename.replace(/\.pdf$/i, '')}.tex`))}>Xuất .tex</button>
              <button type="button" className="text-button history-delete" disabled={PROCESSING_STATES.has(item.status)} onClick={() => onPerform(() => onDelete(item))}>Xóa</button>
            </div>
          </li>
        ))}
      </ul>
      {history.length < historyTotal && (
        <button type="button" className="text-button" onClick={onLoadMore} disabled={historyLoading}>
          {historyLoading ? 'Đang tải…' : 'Xem thêm'}
        </button>
      )}
    </section>
  )
}
