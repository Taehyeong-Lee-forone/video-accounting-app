#!/usr/bin/env python3
"""
データベース状態詳細確認
"""
import requests
import json

BASE_URL = "https://video-accounting-app.onrender.com"

def check_database_and_users():
    print("="*50)
    print("Supabase データベース状態確認")
    print("="*50)
    
    # 1. DB情報確認
    db_info = requests.get(f"{BASE_URL}/db-info").json()
    print(f"\n📊 データベース統計:")
    print(f"   Type: {db_info.get('database_type')}")
    print(f"   Users: {db_info.get('statistics', {}).get('users')}名")
    print(f"   Videos: {db_info.get('statistics', {}).get('videos')}個")
    print(f"   Receipts: {db_info.get('statistics', {}).get('receipts')}個")
    
    # 2. 既知のアカウントでログインテスト
    print("\n" + "="*50)
    print("ログインテスト")
    print("="*50)
    
    accounts = [
        {"username": "admin", "password": "admin123"},
        {"username": "admin@example.com", "password": "admin123"},
    ]
    
    for acc in accounts:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": acc['username'], "password": acc['password']}
        )
        
        if response.status_code == 200:
            print(f"✅ {acc['username']}: ログイン成功")
            
            # ユーザー情報取得
            token = response.json()['access_token']
            user_info = requests.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            ).json()
            
            print(f"   - ID: {user_info.get('id')}")
            print(f"   - Email: {user_info.get('email')}")
            print(f"   - Username: {user_info.get('username')}")
            print(f"   - Superuser: {user_info.get('is_superuser')}")
        else:
            print(f"❌ {acc['username']}: ログイン失敗 ({response.status_code})")

if __name__ == "__main__":
    check_database_and_users()