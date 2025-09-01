"""
データ同期API
ローカルとプロダクション間でデータを同期する
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
from datetime import datetime
from database import get_db
from models import User, Video, Frame, Receipt, JournalEntry
from routers.auth_v2 import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/data/export")
async def export_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    現在のユーザーのデータをエクスポート
    """
    try:
        # ユーザーの動画を取得
        videos = db.query(Video).filter(Video.user_id == current_user.id).all()
        
        export_data = {
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email
            },
            "videos": [],
            "exported_at": datetime.now().isoformat()
        }
        
        for video in videos:
            video_data = {
                "id": video.id,
                "filename": video.filename,
                "cloud_url": video.cloud_url,
                "local_path": video.local_path,
                "gcs_uri": video.gcs_uri,
                "created_at": video.created_at.isoformat() if video.created_at else None,
                "status": video.status,
                "thumbnail_path": video.thumbnail_path,
                "frames": [],
                "receipts": [],
                "journal_entries": []
            }
            
            # フレームデータ
            for frame in video.frames:
                frame_data = {
                    "time_ms": frame.time_ms,
                    "sharpness": frame.sharpness,
                    "brightness": frame.brightness,
                    "contrast": frame.contrast,
                    "ocr_text": frame.ocr_text,
                    "is_best": frame.is_best,
                    "frame_score": frame.frame_score
                }
                video_data["frames"].append(frame_data)
            
            # レシートデータ
            for receipt in video.receipts:
                receipt_data = {
                    "vendor": receipt.vendor,
                    "vendor_norm": receipt.vendor_norm,
                    "total": float(receipt.total) if receipt.total else None,
                    "subtotal": float(receipt.subtotal) if receipt.subtotal else None,
                    "tax": float(receipt.tax) if receipt.tax else None,
                    "tax_rate": float(receipt.tax_rate) if receipt.tax_rate else None,
                    "issue_date": receipt.issue_date.isoformat() if receipt.issue_date else None,
                    "payment_method": receipt.payment_method,
                    "document_type": receipt.document_type,
                    "status": receipt.status,
                    "memo": receipt.memo
                }
                video_data["receipts"].append(receipt_data)
            
            # 仕訳データ
            for entry in video.journal_entries:
                entry_data = {
                    "time_ms": entry.time_ms,
                    "debit_account": entry.debit_account,
                    "credit_account": entry.credit_account,
                    "debit_amount": float(entry.debit_amount) if entry.debit_amount else None,
                    "credit_amount": float(entry.credit_amount) if entry.credit_amount else None,
                    "tax_account": entry.tax_account,
                    "tax_amount": float(entry.tax_amount) if entry.tax_amount else None,
                    "status": entry.status
                }
                video_data["journal_entries"].append(entry_data)
            
            export_data["videos"].append(video_data)
        
        logger.info(f"データエクスポート成功: {len(export_data['videos'])}件の動画")
        
        return export_data
        
    except Exception as e:
        logger.error(f"データエクスポートエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/data/import")
async def import_data(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    データをインポート（マージ）
    """
    try:
        imported_count = 0
        
        for video_data in data.get("videos", []):
            # 既存の動画をチェック（storage_pathで重複確認）
            existing_video = db.query(Video).filter(
                Video.storage_path == video_data.get("storage_path"),
                Video.user_id == current_user.id
            ).first()
            
            if existing_video:
                logger.info(f"動画既存: {video_data['filename']}")
                continue
            
            # 新しい動画を作成
            new_video = Video(
                user_id=current_user.id,
                filename=video_data["filename"],
                file_url=video_data.get("file_url"),
                storage_path=video_data.get("storage_path"),
                processed=video_data.get("processed", False),
                status=video_data.get("status", "completed"),
                thumbnail_url=video_data.get("thumbnail_url")
            )
            
            if video_data.get("uploaded_at"):
                new_video.uploaded_at = datetime.fromisoformat(video_data["uploaded_at"])
            
            db.add(new_video)
            db.flush()  # IDを取得
            
            # フレームを追加
            for frame_data in video_data.get("frames", []):
                new_frame = Frame(
                    video_id=new_video.id,
                    frame_number=frame_data["frame_number"],
                    timestamp=frame_data["timestamp"],
                    file_url=frame_data.get("file_url"),
                    storage_path=frame_data.get("storage_path"),
                    has_receipt=frame_data.get("has_receipt", False),
                    confidence_score=frame_data.get("confidence_score")
                )
                db.add(new_frame)
            
            # レシートを追加
            for receipt_data in video_data.get("receipts", []):
                new_receipt = Receipt(
                    video_id=new_video.id,
                    store_name=receipt_data.get("store_name"),
                    total_amount=receipt_data.get("total_amount"),
                    tax_amount=receipt_data.get("tax_amount"),
                    date=datetime.fromisoformat(receipt_data["date"]) if receipt_data.get("date") else None,
                    items=json.dumps(receipt_data.get("items", [])),
                    payment_method=receipt_data.get("payment_method"),
                    confidence_score=receipt_data.get("confidence_score"),
                    ai_analysis=json.dumps(receipt_data.get("ai_analysis")) if receipt_data.get("ai_analysis") else None
                )
                db.add(new_receipt)
                db.flush()
                
                # 仕訳を追加
                for entry_data in video_data.get("journal_entries", []):
                    new_entry = JournalEntry(
                        receipt_id=new_receipt.id,
                        video_id=new_video.id,
                        date=datetime.fromisoformat(entry_data["date"]) if entry_data.get("date") else None,
                        description=entry_data.get("description"),
                        debit_account=entry_data.get("debit_account"),
                        credit_account=entry_data.get("credit_account"),
                        amount=entry_data.get("amount"),
                        tax_amount=entry_data.get("tax_amount"),
                        tax_rate=entry_data.get("tax_rate"),
                        memo=entry_data.get("memo")
                    )
                    db.add(new_entry)
            
            imported_count += 1
        
        db.commit()
        
        logger.info(f"データインポート成功: {imported_count}件の動画")
        
        return {
            "success": True,
            "imported_count": imported_count,
            "message": f"{imported_count}件の動画をインポートしました"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"データインポートエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/data/sync-status")
async def sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    同期ステータスを確認
    """
    try:
        video_count = db.query(Video).filter(Video.user_id == current_user.id).count()
        receipt_count = db.query(Receipt).join(Video).filter(Video.user_id == current_user.id).count()
        journal_count = db.query(JournalEntry).join(Video).filter(Video.user_id == current_user.id).count()
        
        return {
            "user": current_user.username,
            "statistics": {
                "videos": video_count,
                "receipts": receipt_count,
                "journal_entries": journal_count
            },
            "storage": "Supabase Storage (共有)",
            "database": "Local/Production (分離)"
        }
        
    except Exception as e:
        logger.error(f"同期ステータスエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))