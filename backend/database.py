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

# DATABASE_URLを取得
DATABASE_URL = os.getenv("DATABASE_URL")

# Render環境では環境変数DATABASE_URLが自動設定される
# それ以外の環境ではローカルSQLiteまたは明示的に指定されたDBを使用

# 環境に応じてデータベースを選択
if os.getenv("RENDER") == "true":
    # Render環境 - 環境変数またはRender PostgreSQLを使用
    if not DATABASE_URL:
        # RenderがPostgreSQLを提供していない場合のエラー
        logger.error("❌ Render環境でDATABASE_URLが設定されていません")
        logger.error("Renderダッシュボードで以下を設定してください:")
        logger.error("1. PostgreSQL データベースを追加")
        logger.error("2. DATABASE_URL環境変数が自動設定されます")
        # 一時的にSQLiteを使用（データは永続化されません）
        DATABASE_URL = "sqlite:///./temp_video_accounting.db"
        logger.warning("⚠️ 一時的にSQLiteを使用 - データは永続化されません！")
    else:
        logger.info("🔷 Render PostgreSQLを使用 - データ永続化保証")
elif DATABASE_URL:
    # 環境変数で指定されたDBを使用
    logger.info(f"指定されたデータベースを使用: {DATABASE_URL[:30]}...")
else:
    # ローカル開発用 - SQLiteを使用（ローカルでは永続化される）
    DATABASE_URL = "sqlite:///./video_accounting.db"
    logger.info("📁 ローカルSQLiteを使用")
    
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