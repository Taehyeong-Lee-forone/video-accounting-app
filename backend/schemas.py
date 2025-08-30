from pydantic import BaseModel, Field, ConfigDict, field_serializer
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
# from enum import Enum  # Enum使用を削除

# 日本タイムゾーン定義
JST = timezone(timedelta(hours=9))

def to_jst(dt: Optional[datetime]) -> Optional[datetime]:
    """UTC時刻を日本時間(JST)に変換"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # タイムゾーンがない場合はUTCとして扱う
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST)

# Enum定義を定数として保持（参照用）
class VideoStatus:
    queued = "queued"
    processing = "processing"
    done = "done"
    error = "error"

class JournalStatus:
    unconfirmed = "unconfirmed"
    confirmed = "confirmed"
    rejected = "rejected"
    pending = "pending"

class DocumentType:
    receipt = "領収書"
    invoice = "請求書"
    slip = "レシート"
    estimate = "見積書"
    other = "その他"
    composite = "請求書・領収書"  # Temporary: handle composite type

class PaymentMethod:
    cash = "現金"
    credit = "クレジット"
    emoney = "電子マネー"
    unknown = "不明"

# Video Schemas
class VideoUpload(BaseModel):
    filename: str

class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    filename: str
    gcs_uri: Optional[str] = None
    local_path: Optional[str] = None
    duration_ms: Optional[int] = None
    status: str
    progress: Optional[int] = None
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    receipts_count: Optional[int] = None  # レシート件数追加
    auto_receipts_count: Optional[int] = None  # 自動抽出レシート件数
    manual_receipts_count: Optional[int] = None  # 手動抽出レシート件数
    
    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime) -> str:
        """created_atを日本時間に変換してISO形式で返却"""
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: Optional[datetime]) -> Optional[str]:
        """updated_atを日本時間に変換してISO形式で返却"""
        if dt is None:
            return None
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()

class VideoAnalyzeRequest(BaseModel):
    frames_per_second: int = Field(default=2, ge=1, le=10)
    reprocess: bool = False

# Frame Schemas
class FrameResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    video_id: int
    time_ms: int
    sharpness: Optional[float] = None
    brightness: Optional[float] = None
    contrast: Optional[float] = None
    ocr_text: Optional[str] = None
    phash: Optional[str] = None
    is_best: bool
    frame_score: Optional[float] = None
    frame_path: Optional[str] = None

# Receipt Schemas
class ReceiptCreate(BaseModel):
    video_id: int
    best_frame_id: int
    vendor: Optional[str] = None
    document_type: Optional[str] = None
    issue_date: Optional[datetime] = None
    currency: str = "JPY"
    total: Optional[float] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tax_rate: Optional[float] = None
    payment_method: Optional[str] = None
    memo: Optional[str] = None

class ReceiptUpdate(BaseModel):
    vendor: Optional[str] = None
    document_type: Optional[str] = None
    issue_date: Optional[datetime] = None
    total: Optional[float] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tax_rate: Optional[float] = None
    payment_method: Optional[str] = None
    memo: Optional[str] = None

class ReceiptHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    receipt_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: str
    changed_at: datetime
    
    @field_serializer('changed_at')
    def serialize_changed_at(self, dt: datetime) -> str:
        """changed_atを日本時間に変換"""
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()

class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    video_id: int
    best_frame_id: Optional[int] = None
    vendor: Optional[str] = None
    vendor_norm: Optional[str] = None
    document_type: Optional[str] = None
    issue_date: Optional[datetime] = None
    currency: str
    total: Optional[float] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tax_rate: Optional[float] = None
    payment_method: Optional[str] = None
    duplicate_of_id: Optional[int] = None
    status: str
    is_manual: Optional[bool] = False  # 手動追加フラグ
    memo: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    best_frame: Optional['FrameResponse'] = None  # フレーム情報追加
    history: List['ReceiptHistoryResponse'] = []  # 修正履歴
    
    @field_serializer('issue_date')
    def serialize_issue_date(self, dt: Optional[datetime]) -> Optional[str]:
        """issue_dateを日本時間に変換"""
        if dt is None:
            return None
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()
    
    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime) -> str:
        """created_atを日本時間に変換"""
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: Optional[datetime]) -> Optional[str]:
        """updated_atを日本時間に変換"""
        if dt is None:
            return None
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()

# Journal Entry Schemas
class JournalEntryCreate(BaseModel):
    receipt_id: int
    video_id: int
    time_ms: int
    debit_account: str
    credit_account: str
    debit_amount: float
    credit_amount: float
    tax_account: Optional[str] = None
    tax_amount: Optional[float] = None
    memo: Optional[str] = None

class JournalEntryUpdate(BaseModel):
    debit_account: Optional[str] = None
    credit_account: Optional[str] = None
    debit_amount: Optional[float] = None
    credit_amount: Optional[float] = None
    tax_account: Optional[str] = None
    tax_amount: Optional[float] = None
    memo: Optional[str] = None
    status: Optional[JournalStatus] = None

class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    receipt_id: int
    video_id: int
    time_ms: Optional[int] = None
    debit_account: Optional[str] = None
    credit_account: Optional[str] = None
    debit_amount: Optional[float] = None
    credit_amount: Optional[float] = None
    tax_account: Optional[str] = None
    tax_amount: Optional[float] = None
    memo: Optional[str] = None
    status: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @field_serializer('confirmed_at')
    def serialize_confirmed_at(self, dt: Optional[datetime]) -> Optional[str]:
        """confirmed_atを日本時間に変換"""
        if dt is None:
            return None
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()
    
    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime) -> str:
        """created_atを日本時間に変換"""
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: Optional[datetime]) -> Optional[str]:
        """updated_atを日本時間に変換"""
        if dt is None:
            return None
        jst_time = to_jst(dt)
        return jst_time.isoformat() if jst_time else dt.isoformat()

class JournalConfirm(BaseModel):
    confirmed_by: str

# Vendor Schemas
class VendorCreate(BaseModel):
    name: str
    default_debit_account: Optional[str] = None
    default_credit_account: Optional[str] = None
    default_tax_rate: Optional[float] = None
    default_payment_method: Optional[str] = None

class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    name_norm: str
    default_debit_account: Optional[str] = None
    default_credit_account: Optional[str] = None
    default_tax_rate: Optional[float] = None
    default_payment_method: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

# Account Schemas
class AccountCreate(BaseModel):
    code: str
    name: str
    type: str
    tax_category: Optional[str] = None

class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    code: str
    name: str
    type: str
    tax_category: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

# Rule Schemas
class RuleCreate(BaseModel):
    pattern: str
    pattern_type: Optional[str] = None
    debit_account: Optional[str] = None
    credit_account: Optional[str] = None
    tax_rate: Optional[float] = None
    priority: int = 0

class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    pattern: str
    pattern_type: Optional[str] = None
    debit_account: Optional[str] = None
    credit_account: Optional[str] = None
    tax_rate: Optional[float] = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

# Video Detail Response with related data
class VideoDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    filename: str
    gcs_uri: Optional[str] = None
    local_path: Optional[str] = None
    duration_ms: Optional[int] = None
    status: str
    progress: Optional[int] = None
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    frames: List[FrameResponse] = []
    receipts: List[ReceiptResponse] = []
    journal_entries: List[JournalEntryResponse] = []