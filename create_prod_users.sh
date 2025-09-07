#!/bin/bash

echo "🔍 프로덕션 사용자 목록 확인..."
curl -s https://video-accounting-app.onrender.com/api/temp/list-users | jq .

echo ""
echo "👤 프로덕션에 사용자 생성..."

# forone.video2@gmail.com 사용자 생성
echo "Creating forone.video2@gmail.com..."
curl -X POST https://video-accounting-app.onrender.com/api/temp/create-user \
  -H "Content-Type: application/json" \
  -d '{
    "email": "forone.video2@gmail.com",
    "username": "forone",
    "password": "test123"
  }' | jq .

echo ""
echo "✅ 완료! 다시 사용자 목록 확인..."
curl -s https://video-accounting-app.onrender.com/api/temp/list-users | jq .