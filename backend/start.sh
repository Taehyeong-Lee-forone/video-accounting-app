#!/bin/sh
# Render環境用起動スクリプト

# 環境変数の確認
echo "=== Environment Check ==="
echo "PORT: ${PORT:-10000}"
echo "DATABASE_URL: ${DATABASE_URL:+Set}"
echo "RENDER: ${RENDER}"
echo "========================"

# PORT環境変数が設定されていない場合のデフォルト値
if [ -z "$PORT" ]; then
    export PORT=10000
fi

# データベースURLチェック
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL is not set!"
    echo "Please set DATABASE_URL in Render Dashboard > Environment Variables"
fi

# サーバー起動
echo "Starting server on port: $PORT"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" --log-level info