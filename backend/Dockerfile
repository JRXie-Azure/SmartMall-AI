# ====== SmartMall-AI Backend Dockerfile ======
FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/uploads /app/chroma_db

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
