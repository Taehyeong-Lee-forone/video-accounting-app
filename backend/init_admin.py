#!/usr/bin/env python3
"""
初期管理者アカウント作成スクリプト
"""
import os
import sys
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import User, Base
import getpass

# パスワードハッシュ設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """パスワードをハッシュ化"""
    return pwd_context.hash(password)

def create_admin_user():
    """管理者ユーザーを作成"""
    db = SessionLocal()
    
    try:
        # テーブルが存在しない場合は作成
        Base.metadata.create_all(bind=engine)
        
        # 既存の管理者を確認
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        if existing_admin:
            print("⚠️ 管理者アカウントは既に存在します")
            update = input("パスワードを更新しますか？ (y/n): ")
            
            if update.lower() == 'y':
                # 環境変数からパスワード取得（本番環境用）
                password = os.getenv("ADMIN_PASSWORD")
                
                if not password:
                    # 開発環境では入力を求める
                    if os.getenv("RENDER") == "true":
                        # Render環境ではデフォルトパスワード
                        password = "admin123!@#"
                        print("⚠️ Render環境のため、デフォルトパスワードを使用します")
                        print("⚠️ 環境変数 ADMIN_PASSWORD を設定してください")
                    else:
                        password = getpass.getpass("新しいパスワード: ")
                        confirm = getpass.getpass("パスワード確認: ")
                        
                        if password != confirm:
                            print("❌ パスワードが一致しません")
                            return
                
                existing_admin.hashed_password = get_password_hash(password)
                db.commit()
                print("✅ 管理者パスワードを更新しました")
            return
        
        # 新規管理者作成
        print("\n🔐 新規管理者アカウントを作成します")
        
        # 環境変数から設定取得
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD")
        
        if not admin_password:
            if os.getenv("RENDER") == "true":
                # Render環境ではデフォルトパスワード
                admin_password = "admin123!@#"
                print("⚠️ Render環境のため、デフォルトパスワードを使用します")
                print("⚠️ 環境変数 ADMIN_PASSWORD を設定してください")
            else:
                # 開発環境では入力を求める
                admin_password = getpass.getpass("管理者パスワード: ")
                confirm = getpass.getpass("パスワード確認: ")
                
                if admin_password != confirm:
                    print("❌ パスワードが一致しません")
                    return
        
        # 管理者ユーザー作成
        admin_user = User(
            email=admin_email,
            username=admin_username,
            hashed_password=get_password_hash(admin_password),
            full_name="System Administrator",
            is_active=True,
            is_superuser=True,
            storage_quota_mb=50000  # 50GB
        )
        
        db.add(admin_user)
        db.commit()
        
        print("\n✅ 管理者アカウントを作成しました")
        print(f"   ユーザー名: {admin_username}")
        print(f"   メール: {admin_email}")
        print("   ログイン後、パスワードを変更してください")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()