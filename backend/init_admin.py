#!/usr/bin/env python3
"""
初期管理者アカウント作成スクリプト
"""
from database import SessionLocal, engine
from models import User
from services.auth_service import get_password_hash

def create_admin_user():
    """初期管理者を作成"""
    db = SessionLocal()
    
    try:
        # 既存の管理者確認
        admin = db.query(User).filter(User.username == "admin").first()
        
        if admin:
            print("✅ 管理者アカウントは既に存在します")
            return
        
        # 新規管理者作成
        admin_user = User(
            email="admin@example.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            is_active=True,
            is_superuser=True,
            storage_quota_mb=50000
        )
        
        db.add(admin_user)
        db.commit()
        
        print("✅ 管理者アカウントを作成しました")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Email: admin@example.com")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
