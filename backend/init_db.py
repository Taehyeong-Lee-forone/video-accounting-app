#!/usr/bin/env python3
"""
データベース初期化スクリプト
Render環境での初回デプロイ時に実行
"""

import os
import sys
from dotenv import load_dotenv
import logging

# 環境変数を読み込む
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """データベースとユーザーを初期化"""
    try:
        from database import engine, Base
        from sqlalchemy.orm import Session
        from models import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
        
        # テーブル作成
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created successfully")
        
        # Admin user作成
        session = Session(engine)
        
        # 既存のadmin確認
        admin = session.query(User).filter_by(username='admin').first()
        if not admin:
            logger.info("Creating admin user...")
            admin = User(
                email='admin@example.com',
                username='admin',
                hashed_password=pwd_context.hash('admin123'),
                full_name='Administrator',
                is_superuser=True,
                is_active=True,
                storage_quota_mb=10000,
                storage_used_mb=0.0
            )
            session.add(admin)
            session.commit()
            logger.info("✅ Admin user created (username: admin, password: admin123)")
        else:
            logger.info("✅ Admin user already exists")
        
        session.close()
        
        logger.info("\n✅ Database initialization complete!")
        logger.info("📝 Default credentials: admin/admin123")
        logger.info("⚠️  Please change the admin password after first login!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Render環境チェック
    if os.getenv("RENDER"):
        logger.info("Running in Render environment")
    else:
        logger.info("Running in local environment")
    
    if init_database():
        sys.exit(0)
    else:
        sys.exit(1)