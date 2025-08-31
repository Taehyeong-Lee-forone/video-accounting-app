#!/usr/bin/env bash
# Render ビルドスクリプト

set -e  # エラーで停止

echo "Starting build process..."

# Python依存関係インストール
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# データベース初期化
echo "Initializing database..."
python init_db.py

echo "Build complete!"