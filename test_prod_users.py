#!/usr/bin/env python3
"""
プロダクション環境のユーザー確認（API経由）
"""
import requests

BASE_URL = "https://video-accounting-app.onrender.com"

def test_known_accounts():
    """既知のアカウントでログインテスト"""
    print("="*50)
    print("プロダクション環境 ユーザーテスト")
    print("="*50)
    
    # 可能性のあるアカウント
    test_accounts = [
        {"username": "admin", "password": "admin123"},
        {"username": "test", "password": "test123"},
        {"username": "user", "password": "user123"},
        {"username": "demo", "password": "demo123"},
        {"username": "taehyeong", "password": "password"},
        {"username": "lee", "password": "password"},
    ]
    
    for account in test_accounts:
        print(f"\nテスト: {account['username']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                data={
                    "username": account['username'],
                    "password": account['password']
                }
            )
            
            if response.status_code == 200:
                print(f"✅ ログイン成功! - {account['username']}")
                data = response.json()
                
                # ユーザー情報取得
                user_response = requests.get(
                    f"{BASE_URL}/api/auth/me",
                    headers={
                        "Authorization": f"Bearer {data['access_token']}"
                    }
                )
                
                if user_response.status_code == 200:
                    user_info = user_response.json()
                    print(f"   Email: {user_info.get('email')}")
                    print(f"   Full Name: {user_info.get('full_name')}")
                    print(f"   Superuser: {user_info.get('is_superuser')}")
            else:
                print(f"❌ ログイン失敗 - {response.status_code}")
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")

if __name__ == "__main__":
    test_known_accounts()