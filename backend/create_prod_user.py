#!/usr/bin/env python3
"""
プ로ダクション環境用ユーザー作成スクリプト
Render環境で実行するためのスクリプト
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import User
from passlib.context import CryptContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_user_in_production():
    # プロダクション環境のDATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.error("DATABASE_URL環境変数が設定されていません")
        return
    
    # PostgreSQL URLの修正（必要な場合）
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    logger.info(f"データベース接続中...")
    engine = create_engine(database_url)
    
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    session = Session(engine)
    
    try:
        # テストユーザー情報
        test_users = [
            {
                "email": "forone.video2@gmail.com",
                "username": "forone",
                "password": "test123",
                "full_name": "Forone Test User"
            },
            {
                "email": "admin@example.com",
                "username": "admin",
                "password": "admin123",
                "full_name": "Administrator",
                "is_superuser": True
            }
        ]
        
        for user_data in test_users:
            # 既存ユーザーチェック
            existing = session.query(User).filter(
                User.email == user_data["email"]
            ).first()
            
            if existing:
                logger.info(f"✅ ユーザー既存: {existing.email}")
            else:
                # 新規ユーザー作成
                user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    hashed_password=pwd_context.hash(user_data["password"]),
                    full_name=user_data["full_name"],
                    is_active=True,
                    is_superuser=user_data.get("is_superuser", False)
                )
                
                session.add(user)
                session.commit()
                logger.info(f"✅ 新規ユーザー作成: {user_data['email']}")
        
        # すべてのユーザーをリスト
        logger.info("\n=== 登録済みユーザー一覧 ===")
        users = session.query(User).all()
        for user in users:
            logger.info(f"  - {user.username}: {user.email}")
            
    except Exception as e:
        logger.error(f"エラー: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_user_in_production()