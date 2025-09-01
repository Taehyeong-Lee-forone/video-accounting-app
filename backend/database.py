from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# デバッグ情報を出力
logger.info(f"RENDER環境: {os.getenv('RENDER', 'false')}")
logger.info(f"DATABASE_URL設定: {'設定済み' if os.getenv('DATABASE_URL') else '未設定'}")

# DATABASE_URLを取得（Render環境では必須）
DATABASE_URL = os.getenv("DATABASE_URL")

# Render環境では必ずPostgreSQLを使用
if os.getenv("RENDER") == "true":
    # Render環境ではUSE_SQLITEを無視
    if not DATABASE_URL:
        logger.error("❌ Render環境でDATABASE_URLが設定されていません")
        raise ValueError("DATABASE_URL is required in Render environment")
    logger.info("Render環境 - PostgreSQL (Supabase)を使用")
elif not DATABASE_URL:
    # ローカル開発環境用のフォールバック
    logger.warning("DATABASE_URL未設定 - SQLiteを使用")
    DATABASE_URL = "sqlite:///./video_accounting.db"
else:
    # URLの一部を隠してログ出力
    if "pooler.supabase.com" in DATABASE_URL:
        logger.info("Supabase Pooler接続を使用")
    elif "supabase.co" in DATABASE_URL:
        logger.warning("⚠️ Direct接続を使用中 - Pooler接続に変更してください")
    
    # パスワード部分を隠してログ出力
    safe_url = DATABASE_URL.split('@')[0].split(':')[0] + ":****@" + DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL[:50]
    logger.info(f"データベースURL: {safe_url}")

# SQLite用の調整
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL接続設定
    # Render PostgreSQLのSSL設定を追加
    connect_args = {}
    if "render.com" in DATABASE_URL:
        # RenderのPostgreSQLはSSL必須
        connect_args = {
            "sslmode": "require"
        }
    
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # 接続の健全性チェック
        pool_recycle=3600,   # 1時間ごとに接続をリサイクル
        connect_args=connect_args
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()