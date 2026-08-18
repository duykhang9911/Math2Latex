# python:3.11-slim: bản Python đã cài sẵn, "slim" = bản rút gọn, ít dung lượng hơn bản đầy đủ
FROM python:3.11-slim

WORKDIR /app

# Copy CHỈ requirements.txt trước để tận dụng cache của Docker khi build lại
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# --host 0.0.0.0: bắt buộc để máy Windows kết nối được vào server trong container
# --reload: tự nạp lại code khi sửa file .py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]