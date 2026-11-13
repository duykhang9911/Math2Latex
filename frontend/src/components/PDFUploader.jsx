export function PDFUploader({ selectedFile, setSelectedFile, busy, onUpload }) {
  return (
    <form className="grid grid-cols-[minmax(0,1fr)_auto] gap-2.5" onSubmit={onUpload}>
      <label className="min-w-0 min-h-12 px-3 flex items-center gap-2.5 border border-[#c8d0c3] bg-white/70 cursor-pointer">
        <input type="file" accept="application/pdf,.pdf" className="absolute w-px h-px opacity-0" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
        <span className="text-lg text-green" aria-hidden="true">↥</span>
        <span className="flex-1 overflow-hidden text-muted text-xs text-ellipsis whitespace-nowrap">{selectedFile?.name || 'Chọn PDF để bắt đầu'}</span>
        <span className="text-green text-[11px] font-bold">Browse</span>
      </label>
      <button className="primary-button" type="submit" disabled={!selectedFile || busy}>
        {busy ? 'Đang xử lý' : 'Tải PDF'} <span aria-hidden="true">→</span>
      </button>
    </form>
  )
}
