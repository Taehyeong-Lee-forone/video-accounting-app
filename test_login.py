#!/usr/bin/env python3
"""
ログインAPIテスト
"""
import requests
import json

# テスト環境
BASE_URL = "https://video-accounting-app.onrender.com"

def test_login():
    """ログインテスト"""
    print("="*50)
    print("ログインAPIテスト")
    print("="*50)
    
    # テストユーザー情報
    test_users = [
        {"email": "test@example.com", "password": "password123"},
        {"email": "admin@example.com", "password": "admin123"},
    ]
    
    for user in test_users:
        print(f"\nテスト: {user['email']}")
        
        # ログイン試行
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json=user
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ ログイン成功!")
                print(f"   - Token: {data.get('access_token', 'N/A')[:20]}...")
                print(f"   - User: {data.get('user', {})}")
            else:
                print(f"❌ ログイン失敗: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")
    
    # 新しい認証エンドポイントもテスト
    print("\n" + "="*50)
    print("auth_v2エンドポイントテスト")
    print("="*50)
    
    for user in test_users:
        print(f"\nテスト (v2): {user['email']}")
        
        try:
            # FormDataとして送信
            response = requests.post(
                f"{BASE_URL}/auth_v2/login",
                data={
                    "username": user['email'],
                    "password": user['password']
                }
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ ログイン成功!")
                print(f"   - Token: {data.get('access_token', 'N/A')[:20]}...")
            else:
                print(f"❌ ログイン失敗: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")

def test_register():
    """新規登録テスト"""
    print("\n" + "="*50)
    print("新規登録APIテスト")
    print("="*50)
    
    import time
    timestamp = int(time.time())
    
    new_user = {
        "email": f"test{timestamp}@example.com",
        "password": "testpass123",
        "name": f"Test User {timestamp}"
    }
    
    print(f"新規ユーザー: {new_user['email']}")
    
    try:
        # 登録
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json=new_user
        )
        
        print(f"Register Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("✅ 登録成功!")
            
            # ログインテスト
            login_response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": new_user['email'],
                    "password": new_user['password']
                }
            )
            
            if login_response.status_code == 200:
                print("✅ 新規ユーザーでログイン成功!")
            else:
                print(f"❌ ログイン失敗: {login_response.text}")
        else:
            print(f"❌ 登録失敗: {response.text}")
            
    except Exception as e:
        print(f"❌ エラー: {str(e)}")

if __name__ == "__main__":
    test_login()
    test_register()