#!/usr/bin/env python3
"""
データベース内の既存ユーザー確認
"""
from database import SessionLocal
from models import User

def check_existing_users():
    """既存ユーザーをリスト表示"""
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        if not users:
            print("❌ ユーザーが登録されていません")
            return
        
        print("="*50)
        print("登録済みユーザー一覧")
        print("="*50)
        
        for user in users:
            print(f"\n👤 User ID: {user.id}")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Full Name: {user.full_name}")
            print(f"   Active: {user.is_active}")
            print(f"   Superuser: {user.is_superuser}")
            print(f"   Created: {user.created_at}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_existing_users()