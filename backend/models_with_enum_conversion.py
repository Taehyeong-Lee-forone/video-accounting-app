"""
임시 해결책: SQLAlchemy에서 enum 값 자동 변환

이 파일은 기존 models.py를 대체하는 대신, 
Video 모델에 enum 값 자동 변환 로직을 추가하는 예시입니다.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, UniqueConstraint, Index, Enum as SQLEnum, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

# 기존 VideoStatus enum은 그대로 유지
class VideoStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    gcs_uri = Column(String(500))
    local_path = Column(String(500))
    thumbnail_path = Column(String(500))
    duration_ms = Column(Integer)
    _status = Column('status', String(20), default="queued", nullable=False)  # 内部的には文字列として保存
    progress = Column(Integer, default=0)
    progress_message = Column(String(500))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    @property
    def status(self):
        """status プロパティ - 大文字小文字を正規化"""
        if self._status:
            # データベースから読み込んだ値を小文字に正規化
            normalized = self._status.lower()
            if normalized == "queued":
                return VideoStatus.QUEUED
            elif normalized == "processing":
                return VideoStatus.PROCESSING
            elif normalized == "done":
                return VideoStatus.DONE
            elif normalized == "error":
                return VideoStatus.ERROR
        return VideoStatus.QUEUED
    
    @status.setter
    def status(self, value):
        """status セッター - 様々な入力形式を受け入れ"""
        if isinstance(value, VideoStatus):
            self._status = value.value  # enum.value = "queued"
        elif isinstance(value, str):
            # 文字列値を小文字に正規化
            normalized = value.lower()
            if normalized in ["queued", "processing", "done", "error"]:
                self._status = normalized
            else:
                # 大文字版も受け入れ（後方互換性）
                upper_to_lower = {
                    "QUEUED": "queued",
                    "PROCESSING": "processing", 
                    "DONE": "done",
                    "ERROR": "error"
                }
                self._status = upper_to_lower.get(value, "queued")
        else:
            self._status = "queued"  # デフォルト値

# SQLAlchemy イベントリスナー - データベース保存前に値を正規化
@event.listens_for(Video, 'before_insert')
@event.listens_for(Video, 'before_update')
def normalize_video_status(mapper, connection, target):
    """データベース保存前にstatus値を正規化"""
    if hasattr(target, '_status') and target._status:
        # 大文字を小文字に変換
        if target._status.upper() in ["QUEUED", "PROCESSING", "DONE", "ERROR"]:
            target._status = target._status.lower()

# 使用例の修正版
"""
# 以下のような使い方ができます:

# 1. 従来通りenumで設定
video.status = VideoStatus.QUEUED

# 2. 文字列で設定（小文字）
video.status = "queued"

# 3. 古いコードとの互換性（大文字）
video.status = "QUEUED"  # 自動的に"queued"に変換

# 4. 読み取り時は常にVideoStatus enumが返される
assert video.status == VideoStatus.QUEUED
assert video.status.value == "queued"
"""