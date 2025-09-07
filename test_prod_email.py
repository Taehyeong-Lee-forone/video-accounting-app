#!/usr/bin/env python3
"""프로덕션 이메일 설정 테스트"""
import requests

# 프로덕션 API 테스트
url = "https://video-accounting-app.onrender.com/api/auth/forgot-password"
data = {"email": "forone.video2@gmail.com"}

print("🔍 프로덕션 비밀번호 재설정 테스트")
print(f"   URL: {url}")
print(f"   Email: {data['email']}")
print()

response = requests.post(url, json=data)
print(f"응답 코드: {response.status_code}")
print(f"응답 내용: {response.json()}")

if response.status_code == 200:
    print("\n✅ API 응답 성공!")
    print("📧 forone.video2@gmail.com 받은편지함을 확인하세요")
    print("   (환경 변수가 설정되어 있다면 메일이 도착할 것입니다)")
else:
    print("\n❌ API 오류 발생")