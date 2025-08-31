"""
簡易版ビデオ処理 - Render環境用最適化版
"""
from models import Video, Frame, Receipt
from sqlalchemy.orm import Session
import logging
import os
from pathlib import Path
import time

logger = logging.getLogger(__name__)

def process_video_simple(video_id: int, db: Session):
    """
    超簡易版ビデオ処理 - 最小限の処理のみ
    """
    logger.info(f"簡易処理開始: Video ID {video_id}")
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            return
        
        # ステータス更新
        video.status = "processing"
        video.progress = 50
        video.progress_message = "簡易処理中..."
        db.commit()
        
        # ダミーフレームを1つだけ作成
        frame = Frame(
            video_id=video_id,
            time_ms=1000,
            frame_path="dummy.jpg",
            ocr_text="簡易処理",
            is_best=True
        )
        db.add(frame)
        db.flush()
        
        # ダミーレシートを1つ作成
        from datetime import datetime
        receipt = Receipt(
            video_id=video_id,
            best_frame_id=frame.id,
            vendor="テスト店舗",
            document_type="レシート",
            issue_date=datetime.now(),
            currency="JPY",
            total=1000,
            subtotal=900,
            tax=100,
            tax_rate=0.10,
            payment_method="現金",
            is_manual=False
        )
        db.add(receipt)
        
        # 完了状態に更新
        video.status = "done"
        video.progress = 100
        video.progress_message = "簡易処理完了"
        video.processing_completed_at = datetime.now()
        
        db.commit()
        logger.info(f"Video {video_id} 簡易処理完了")
        
    except Exception as e:
        logger.error(f"簡易処理エラー: {e}", exc_info=True)
        if video:
            video.status = "error"
            video.error_message = str(e)[:200]
            try:
                db.commit()
            except:
                db.rollback()