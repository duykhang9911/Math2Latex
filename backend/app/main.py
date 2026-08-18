from fastapi import FastAPI

# Khởi tạo app - đây là điểm trung tâm, mọi route (endpoint) sau này đều "gắn" vào biến app này
app = FastAPI(title="Math2Latex API")

# Endpoint kiểm tra sức khoẻ hệ thống - quy ước phổ biến trong mọi API thực tế,
# dùng để: (1) tự kiểm tra backend còn sống không, (2) sau này Docker/hạ tầng
# có thể tự động ping route này để biết container có "khoẻ" không
@app.get("/health")
def health():
    return {"status": "ok"}
