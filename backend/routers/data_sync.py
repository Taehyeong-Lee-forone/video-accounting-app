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
            # 既存の動画をチェック（filenameで重複確認）
            existing_video = db.query(Video).filter(
                Video.filename == video_data.get("filename"),
                Video.user_id == current_user.id
            ).first()
            
            if existing_video:
                logger.info(f"動画既存: {video_data['filename']}")
                continue
            
            # 新しい動画を作成
            new_video = Video(
                user_id=current_user.id,
                filename=video_data["filename"],
                cloud_url=video_data.get("cloud_url"),
                local_path=video_data.get("local_path"),
                gcs_uri=video_data.get("gcs_uri"),
                status=video_data.get("status", "done"),
                thumbnail_path=video_data.get("thumbnail_path")
            )
            
            if video_data.get("created_at"):
                new_video.created_at = datetime.fromisoformat(video_data["created_at"])
            
            db.add(new_video)
            db.flush()  # IDを取得
            
            # フレームを追加
            for frame_data in video_data.get("frames", []):
                new_frame = Frame(
                    video_id=new_video.id,
                    time_ms=frame_data.get("time_ms", 0),
                    sharpness=frame_data.get("sharpness"),
                    brightness=frame_data.get("brightness"),
                    contrast=frame_data.get("contrast"),
                    ocr_text=frame_data.get("ocr_text"),
                    is_best=frame_data.get("is_best", False),
                    frame_score=frame_data.get("frame_score")
                )
                db.add(new_frame)
            
            # レシートを追加
            for receipt_data in video_data.get("receipts", []):
                new_receipt = Receipt(
                    video_id=new_video.id,
                    vendor=receipt_data.get("vendor"),
                    vendor_norm=receipt_data.get("vendor_norm"),
                    total=receipt_data.get("total"),
                    subtotal=receipt_data.get("subtotal"),
                    tax=receipt_data.get("tax"),
                    tax_rate=receipt_data.get("tax_rate"),
                    issue_date=datetime.fromisoformat(receipt_data["issue_date"]) if receipt_data.get("issue_date") else None,
                    payment_method=receipt_data.get("payment_method"),
                    document_type=receipt_data.get("document_type"),
                    status=receipt_data.get("status", "unconfirmed"),
                    memo=receipt_data.get("memo")
                )
                db.add(new_receipt)
                db.flush()
                
            # 仕訳を追加 (receiptとは独立して追加)
            for entry_data in video_data.get("journal_entries", []):
                # 対応するレシートを探す（簡易的にインデックスで対応）
                receipt_id = None
                if video_data.get("receipts"):
                    # 最初のレシートに関連付け（実際の実装では適切なマッピングが必要）
                    first_receipt = db.query(Receipt).filter(
                        Receipt.video_id == new_video.id
                    ).first()
                    if first_receipt:
                        receipt_id = first_receipt.id
                
                if receipt_id:
                    new_entry = JournalEntry(
                        receipt_id=receipt_id,
                        video_id=new_video.id,
                        time_ms=entry_data.get("time_ms"),
                        debit_account=entry_data.get("debit_account"),
                        credit_account=entry_data.get("credit_account"),
                        debit_amount=entry_data.get("debit_amount"),
                        credit_amount=entry_data.get("credit_amount"),
                        tax_account=entry_data.get("tax_account"),
                        tax_amount=entry_data.get("tax_amount"),
                        status=entry_data.get("status", "unconfirmed")
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