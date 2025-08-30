#!/bin/sh
# Render環境用起動スクリプト

# ポート設定の確認
echo "Starting server on port: ${PORT:-10000}"

# PORT環境変数が設定されていない場合のデフォルト値
if [ -z "$PORT" ]; then
    export PORT=10000
fi

# サーバー起動
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"