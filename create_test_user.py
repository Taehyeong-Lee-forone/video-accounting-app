#!/usr/bin/env python3
"""
테스트 사용자 생성
"""
import requests
import json
import time

BASE_URL = "https://video-accounting-app.onrender.com"

def create_test_user():
    """테스트 사용자 생성"""
    timestamp = int(time.time())
    
    # 새 사용자 정보
    new_user = {
        "email": f"test{timestamp}@example.com",
        "username": f"testuser{timestamp}",
        "password": "password123",
        "full_name": f"Test User {timestamp}"
    }
    
    print("="*50)
    print("새 사용자 생성 테스트")
    print("="*50)
    print(f"Username: {new_user['username']}")
    print(f"Email: {new_user['email']}")
    print(f"Password: {new_user['password']}")
    
    # 회원가입
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=new_user
    )
    
    print(f"\n등록 응답: {response.status_code}")
    if response.status_code in [200, 201]:
        print("✅ 회원가입 성공!")
        user_data = response.json()
        print(f"   User ID: {user_data.get('id')}")
        
        # 로그인 테스트
        print("\n로그인 테스트...")
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": new_user['username'],
                "password": new_user['password']
            }
        )
        
        if login_response.status_code == 200:
            print("✅ 로그인 성공!")
            print("\n이제 이 계정으로 로그인할 수 있습니다:")
            print(f"   Username: {new_user['username']}")
            print(f"   Password: {new_user['password']}")
        else:
            print(f"❌ 로그인 실패: {login_response.text}")
    else:
        print(f"❌ 회원가입 실패: {response.text}")
    
    # DB 상태 재확인
    print("\n" + "="*50)
    print("데이터베이스 상태")
    print("="*50)
    db_info = requests.get(f"{BASE_URL}/db-info").json()
    print(f"총 사용자 수: {db_info['statistics']['users']}명")

if __name__ == "__main__":
    create_test_user()