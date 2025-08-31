#!/usr/bin/env python3
"""
Supabase 데이터베이스의 모든 사용자 확인
"""
import requests
import json

BASE_URL = "https://video-accounting-app.onrender.com"

def get_all_users():
    """API를 통해 데이터베이스 정보 확인"""
    print("="*50)
    print("Supabase 데이터베이스 사용자 확인")
    print("="*50)
    
    # 먼저 admin으로 로그인
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    
    if login_response.status_code != 200:
        print("❌ Admin 로그인 실패")
        return
    
    token = login_response.json()['access_token']
    
    # DB 정보 확인
    db_response = requests.get(f"{BASE_URL}/db-info")
    if db_response.status_code == 200:
        db_info = db_response.json()
        print(f"\n📊 데이터베이스 통계:")
        print(f"   - 데이터베이스 타입: {db_info.get('database_type', 'Unknown')}")
        print(f"   - 총 사용자 수: {db_info.get('statistics', {}).get('users', 0)}명")
        print(f"   - 총 비디오 수: {db_info.get('statistics', {}).get('videos', 0)}개")
        print(f"   - 총 영수증 수: {db_info.get('statistics', {}).get('receipts', 0)}개")
    
    # 최근 생성된 사용자 확인을 위한 더미 로그인 시도
    print("\n" + "="*50)
    print("최근 생성 가능한 사용자명 테스트")
    print("="*50)
    
    possible_usernames = [
        "test", "test1", "test2", "test3",
        "user", "user1", "user2", 
        "demo", "taehyeong", "lee",
        "testuser", "newuser"
    ]
    
    found_users = []
    
    for username in possible_usernames:
        # 각 사용자명으로 로그인 시도
        for password in ["password", "password123", "test123", "1234", "123456"]:
            try:
                response = requests.post(
                    f"{BASE_URL}/api/auth/login",
                    data={
                        "username": username,
                        "password": password
                    },
                    timeout=2
                )
                
                if response.status_code == 200:
                    print(f"✅ 발견: {username} (비밀번호: {password})")
                    
                    # 사용자 정보 가져오기
                    user_token = response.json()['access_token']
                    user_info_response = requests.get(
                        f"{BASE_URL}/api/auth/me",
                        headers={"Authorization": f"Bearer {user_token}"}
                    )
                    
                    if user_info_response.status_code == 200:
                        user_data = user_info_response.json()
                        print(f"   - Email: {user_data.get('email')}")
                        print(f"   - Full Name: {user_data.get('full_name')}")
                        print(f"   - Created: {user_data.get('created_at', 'Unknown')}")
                        found_users.append(username)
                    break
                    
            except Exception:
                continue
    
    if not found_users:
        print("\n⚠️ admin 외에 다른 사용자를 찾을 수 없습니다.")
        print("프론트엔드에서 새로 계정을 생성했다면, 사용한 username과 password를 알려주세요.")
    else:
        print(f"\n📋 총 {len(found_users) + 1}명의 사용자 발견 (admin 포함)")

if __name__ == "__main__":
    get_all_users()