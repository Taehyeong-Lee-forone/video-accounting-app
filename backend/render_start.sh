#!/bin/bash

echo "=== Render Startup Script ==="
echo "Starting application on Render..."

# Render環境変数を設定
export RENDER=true

# PostgreSQL URLが設定されていない場合、Render内部のPostgreSQLを使用
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️ DATABASE_URL not set - using Render PostgreSQL"
    # RenderのPostgreSQLサービスURLを使用
    export DATABASE_URL="$DATABASE_URL"
fi

# Supabase Storage設定
export STORAGE_TYPE=supabase
export SUPABASE_URL=https://cphbbpvhfbmwqkcrhhwm.supabase.co
export SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNwaGJicHZoZmJtd3FrY3JoaHdtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ3ODA0MzksImV4cCI6MjA1MDM1NjQzOX0.5ivGPDz_7dTR_5q4dAjtEFMYGXKzfFPh94qQX_3CKnI
export SUPABASE_BUCKET=videos

echo "Environment variables:"
echo "RENDER=$RENDER"
echo "DATABASE_URL=${DATABASE_URL:0:30}..."
echo "STORAGE_TYPE=$STORAGE_TYPE"

# アプリケーション起動
echo "Starting FastAPI application..."
python3 main.py