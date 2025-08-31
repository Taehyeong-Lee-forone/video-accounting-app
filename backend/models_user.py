"""
ユーザー管理モデル
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    """ユーザーテーブル"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # アカウント設定
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # ストレージ割当量（MB単位）
    storage_quota_mb = Column(Integer, default=10000)  # デフォルト10GB
    storage_used_mb = Column(Integer, default=0)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    # リレーション
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="user", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_username", "username"),
    )
    
    def has_storage_space(self, file_size_mb: float) -> bool:
        """ストレージ容量チェック"""
        return (self.storage_used_mb + file_size_mb) <= self.storage_quota_mb


class UserSession(Base):
    """ユーザーセッション管理"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    
    # セッション情報
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # 有効期限
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    user = relationship("User")
    
    __table_args__ = (
        Index("idx_session_token", "session_token"),
        Index("idx_session_user", "user_id"),
        Index("idx_session_expires", "expires_at"),
    )