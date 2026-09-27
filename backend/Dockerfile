# python:3.11-slim: bản Python đã cài sẵn, "slim" = bản rút gọn, ít dung lượng hơn bản đầy đủ
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends libxcb1 libgl1 libglib2.0-0 \
	&& rm -rf /var/lib/apt/lists/*

# Copy CHỈ requirements.txt trước để tận dụng cache của Docker khi build lại
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip uninstall -y onnxruntime \
	&& pip install --no-cache-dir onnxruntime-gpu

COPY . .

# --host 0.0.0.0: bắt buộc để máy Windows kết nối được vào server trong container
# --reload: tự nạp lại code khi sửa file .py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]