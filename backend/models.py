from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, UniqueConstraint, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class VideoStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"

class JournalStatus(str, enum.Enum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    PENDING = "pending"

class DocumentType(str, enum.Enum):
    RECEIPT = "領収書"
    INVOICE = "請求書"
    SLIP = "レシート"
    ESTIMATE = "見積書"
    OTHER = "その他"
    # Temporary: Accept composite type and map to INVOICE
    COMPOSITE = "請求書・領収書"  # Will be mapped to INVOICE internally

class PaymentMethod(str, enum.Enum):
    CASH = "現金"
    CREDIT = "クレジット"
    EMONEY = "電子マネー"
    UNKNOWN = "不明"

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    gcs_uri = Column(String(500))
    local_path = Column(String(500))
    thumbnail_path = Column(String(500))  # サムネイルパス追加
    duration_ms = Column(Integer)
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.QUEUED, nullable=False)
    progress = Column(Integer, default=0)  # 進行率 0-100
    progress_message = Column(String(500))  # 現在進行中の作業説明
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    frames = relationship("Frame", back_populates="video", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="video", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="video", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_video_status", "status"),
        Index("idx_video_created", "created_at"),
    )

class Frame(Base):
    __tablename__ = "frames"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    time_ms = Column(Integer, nullable=False)
    sharpness = Column(Float)
    brightness = Column(Float)
    contrast = Column(Float)
    ocr_text = Column(Text)
    phash = Column(String(64))
    dhash = Column(String(64))  # difference hash for additional comparison
    is_best = Column(Boolean, default=False)
    is_manual = Column(Boolean, default=False)  # 手動追加フラグ
    ocr_boxes_json = Column(Text)  # JSON string of bounding boxes
    frame_score = Column(Float)
    # 新しい追跡フィールド
    doc_quad_json = Column(Text)  # JSON string of document quadrilateral [[x,y], [x,y], ...]
    sharpness_score = Column(Float)
    doc_area_score = Column(Float)
    perspective_score = Column(Float)
    exposure_score = Column(Float)
    stability_score = Column(Float)
    glare_penalty = Column(Float)
    textness_score = Column(Float)
    total_quality_score = Column(Float)  # Weighted combination of all scores
    motion_score = Column(Float)  # Motion/instability from sampling
    frame_path = Column(String(500))
    
    video = relationship("Video", back_populates="frames")
    receipts = relationship("Receipt", back_populates="best_frame")
    
    __table_args__ = (
        Index("idx_frame_video_time", "video_id", "time_ms"),
        Index("idx_frame_best", "video_id", "is_best"),
        Index("idx_frame_phash", "phash"),
    )

class Receipt(Base):
    __tablename__ = "receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    best_frame_id = Column(Integer, ForeignKey("frames.id", ondelete="SET NULL"))
    vendor = Column(String(255))
    vendor_norm = Column(String(255))  # 正規化されたベンダー名
    document_type = Column(SQLEnum(DocumentType))
    issue_date = Column(DateTime)
    currency = Column(String(3), default="JPY")
    total = Column(Float)
    subtotal = Column(Float)
    tax = Column(Float)
    tax_rate = Column(Float)
    payment_method = Column(SQLEnum(PaymentMethod))
    duplicate_of_id = Column(Integer, ForeignKey("receipts.id", ondelete="SET NULL"))
    normalized_text_hash = Column(String(64))
    status = Column(SQLEnum(JournalStatus), default=JournalStatus.UNCONFIRMED)
    is_manual = Column(Boolean, default=False)  # 手動追加フラグ
    memo = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    video = relationship("Video", back_populates="receipts")
    best_frame = relationship("Frame", back_populates="receipts")
    duplicate_of = relationship("Receipt", remote_side=[id])
    journal_entries = relationship("JournalEntry", back_populates="receipt", cascade="all, delete-orphan")
    history = relationship("ReceiptHistory", back_populates="receipt", cascade="all, delete-orphan", order_by="desc(ReceiptHistory.changed_at)")
    
    __table_args__ = (
        UniqueConstraint("vendor_norm", "issue_date", "total", name="uq_receipt_duplicate"),
        Index("idx_receipt_vendor", "vendor_norm"),
        Index("idx_receipt_date", "issue_date"),
        Index("idx_receipt_hash", "normalized_text_hash"),
    )

class ReceiptHistory(Base):
    __tablename__ = "receipt_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(50), nullable=False)  # 変更されたフィールド
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String(100), default="user")
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    receipt = relationship("Receipt", back_populates="history")
    
    __table_args__ = (
        Index("idx_history_receipt", "receipt_id"),
        Index("idx_history_changed", "changed_at"),
    )

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    time_ms = Column(Integer)
    debit_account = Column(String(100))
    credit_account = Column(String(100))
    debit_amount = Column(Float)
    credit_amount = Column(Float)
    tax_account = Column(String(100))
    tax_amount = Column(Float)
    memo = Column(Text)
    status = Column(SQLEnum(JournalStatus), default=JournalStatus.UNCONFIRMED)
    confirmed_by = Column(String(100))
    confirmed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    receipt = relationship("Receipt", back_populates="journal_entries")
    video = relationship("Video", back_populates="journal_entries")
    
    __table_args__ = (
        Index("idx_journal_status", "status"),
        Index("idx_journal_receipt", "receipt_id"),
        Index("idx_journal_created", "created_at"),
    )

class Vendor(Base):
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    name_norm = Column(String(255), nullable=False, unique=True)
    default_debit_account = Column(String(100))
    default_credit_account = Column(String(100))
    default_tax_rate = Column(Float)
    default_payment_method = Column(SQLEnum(PaymentMethod))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_vendor_norm", "name_norm"),
    )

class Account(Base):
    __tablename__ = "accounts"
    
    code = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 資産, 負債, 純資産, 収益, 費用
    tax_category = Column(String(50))  # 課税, 非課税, 不課税
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_account_type", "type"),
        Index("idx_account_active", "is_active"),
    )

class Rule(Base):
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String(255), nullable=False)  # 正規表現パターン
    pattern_type = Column(String(50))  # vendor, item, amount_range
    debit_account = Column(String(100))
    credit_account = Column(String(100))
    tax_rate = Column(Float)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_rule_priority", "priority"),
        Index("idx_rule_active", "is_active"),
    )