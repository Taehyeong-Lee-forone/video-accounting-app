"""
Vercel Functions用データベース接続ユーティリティ
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# データベースURL取得
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# PostgreSQL URLの形式修正
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLAlchemy設定
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 接続確認
    pool_recycle=300,    # 5分で接続リサイクル
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"  # 30秒タイムアウト
    } if DATABASE_URL.startswith("postgresql") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Session:
    """データベースセッション取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()