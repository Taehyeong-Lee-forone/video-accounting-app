from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./video_accounting.db")

# Render環境でSupabaseを使用する場合の設定
if os.getenv("RENDER") == "true":
    # Supabase Connection Pooling URLを使用（Pooler endpoint）
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
    
    if SUPABASE_URL and SUPABASE_PASSWORD:
        # Supabase PoolerモードのURL形式
        # postgresql://postgres.[project-ref]:[password]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
        DATABASE_URL = f"postgresql://postgres.{SUPABASE_URL}:{SUPABASE_PASSWORD}@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres?sslmode=require"
        logger.info("Supabase Pooler接続URL構築完了")
    elif os.getenv("DATABASE_URL"):
        # 直接DATABASE_URLが設定されている場合
        DATABASE_URL = os.getenv("DATABASE_URL")
        logger.info("DATABASE_URL環境変数を使用")

logger.info(f"データベース接続URL: {DATABASE_URL[:30]}...")

# SQLite用の調整
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL接続設定
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # 接続の健全性チェック
        pool_recycle=3600    # 1時間ごとに接続をリサイクル
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()