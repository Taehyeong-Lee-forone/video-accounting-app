#!/usr/bin/env python3
"""
テストユーザー作成スクリプト
実際のメールアドレスでユーザーを作成
"""
import sys
sys.path.append('backend')

from database import engine
from sqlalchemy.orm import Session
from models import User
from passlib.context import CryptContext
import random
import string

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

def create_test_user():
    session = Session(engine)
    
    # テスト用のメールアドレス
    test_email = "forone.video2@gmail.com"
    test_username = "testuser"
    test_password = "test123"
    
    try:
        # 既存ユーザーチェック
        existing = session.query(User).filter(
            (User.email == test_email) | (User.username == test_username)
        ).first()
        
        if existing:
            print(f"ユーザー既存: {existing.username} ({existing.email})")
            return existing
        
        # 新規ユーザー作成
        user = User(
            email=test_email,
            username=test_username,
            hashed_password=pwd_context.hash(test_password),
            full_name="Test User",
            is_active=True
        )
        
        session.add(user)
        session.commit()
        
        print(f"✅ テストユーザー作成成功!")
        print(f"   Email: {test_email}")
        print(f"   Username: {test_username}")
        print(f"   Password: {test_password}")
        
        return user
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        session.rollback()
        return None
    finally:
        session.close()

if __name__ == "__main__":
    print("=== テストユーザー作成 ===")
    user = create_test_user()
    
    if user:
        print("\n📧 パスワードリセットテスト用:")
        print(f"   curl -X POST http://localhost:5001/api/auth/forgot-password \\")
        print(f"     -H 'Content-Type: application/json' \\")
        print(f"     -d '{{\"email\": \"{user.email}\"}}'")