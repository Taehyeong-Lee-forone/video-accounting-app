FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    postgresql-client \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# 起動スクリプトに実行権限を付与
RUN chmod +x /app/start.sh

# Renderのポート設定
EXPOSE 10000

# シェルスクリプトを使用して起動（環境変数を正しく展開）
CMD ["/bin/sh", "/app/start.sh"]