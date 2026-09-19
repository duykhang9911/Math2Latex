import { useState } from 'react'
import './App.css'

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [status, setStatus] = useState('')
  const [fileInfo, setFileInfo] = useState(null)
  const [isUploading, setIsUploading] = useState(false)

  const handleFileChange = (event) => {
    const file = event.target.files[0]
    setSelectedFile(file)
    setStatus('')
    setFileInfo(null)
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setStatus('Vui lòng chọn file trước khi upload.')
      return
    }

    setIsUploading(true)
    setStatus('Đang upload...')

    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      // Đổi URL: route giờ nằm trong router documents, có prefix /api/documents
      const response = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Upload thất bại')
      }

      // data giờ có dạng { document_id, status } - đã đổi từ { filename, size, path }
      setFileInfo(data)
      setStatus(`Upload thành công! Document ID: ${data.document_id}`)
    } catch (error) {
      setStatus(error.message || 'Có lỗi xảy ra khi upload.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="upload-card">
        <p className="eyebrow">Math2Latex</p>
        <h1>Upload tài liệu toán học</h1>
        <p className="subtitle">
          Tải lên ảnh hoặc PDF chứa công thức toán để tiếp tục xử lý sang LaTeX.
        </p>

        <label className="file-picker">
          <input type="file" onChange={handleFileChange} />
          <span>Chọn file</span>
        </label>

        {selectedFile && (
          <div className="file-meta">
            <strong>Tên file:</strong> {selectedFile.name}
          </div>
        )}

        <button className="upload-button" onClick={handleUpload} disabled={isUploading}>
          {isUploading ? 'Đang upload...' : 'Upload'}
        </button>

        {status && <p className="status">{status}</p>}

        {fileInfo && (
          <div className="result-box">
            <h3>Kết quả upload</h3>
            <p>
              <strong>Document ID:</strong> {fileInfo.document_id}
            </p>
            <p>
              <strong>Trạng thái:</strong> {fileInfo.status}
            </p>
          </div>
        )}
      </section>
    </main>
  )
}

export default App