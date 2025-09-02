#!/bin/bash

# Render Build Script
echo "=== Render Build Script ==="

# Python dependencies 설치
pip install --upgrade pip
pip install -r requirements.txt

# PostgreSQL 클라이언트 라이브러리 설치
pip install psycopg2-binary

echo "Build completed successfully!"