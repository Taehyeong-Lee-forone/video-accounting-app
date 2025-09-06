from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from database import get_db
from models import JournalEntry, Receipt
from schemas import JournalEntryResponse, JournalEntryUpdate, JournalConfirm
from services.journal_generator import JournalGenerator

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[JournalEntryResponse])
async def list_journals(
    video_id: int = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """仕訳一覧取得"""
    query = db.query(JournalEntry)
    
    if video_id:
        query = query.filter(JournalEntry.video_id == video_id)
    if status:
        query = query.filter(JournalEntry.status == status)
    
    journals = query.offset(skip).limit(limit).all()
    return journals

@router.get("/{journal_id}", response_model=JournalEntryResponse)
async def get_journal(journal_id: int, db: Session = Depends(get_db)):
    """仕訳詳細取得"""
    journal = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not journal:
        raise HTTPException(404, "仕訳が見つかりません")
    return journal

@router.patch("/{journal_id}", response_model=JournalEntryResponse)
async def update_journal(
    journal_id: int,
    update: JournalEntryUpdate,
    db: Session = Depends(get_db)
):
    """仕訳更新"""
    journal = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not journal:
        raise HTTPException(404, "仕訳が見つかりません")
    
    update_data = update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(journal, field, value)
    
    journal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(journal)
    
    return journal

@router.post("/{journal_id}/confirm", response_model=JournalEntryResponse)
async def confirm_journal(
    journal_id: int,
    confirm_data: JournalConfirm,
    db: Session = Depends(get_db)
):
    """仕訳承認"""
    journal = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not journal:
        raise HTTPException(404, "仕訳が見つかりません")
    
    journal.status = "confirmed"
    journal.confirmed_by = confirm_data.confirmed_by
    journal.confirmed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(journal)
    
    return journal

@router.post("/{journal_id}/reject", response_model=JournalEntryResponse)
async def reject_journal(
    journal_id: int,
    db: Session = Depends(get_db)
):
    """仕訳差戻し"""
    journal = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not journal:
        raise HTTPException(404, "仕訳が見つかりません")
    
    journal.status = "rejected"
    journal.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(journal)
    
    return journal

@router.delete("/{journal_id}")
async def delete_journal(
    journal_id: int,
    db: Session = Depends(get_db)
):
    """仕訳削除"""
    journal = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not journal:
        raise HTTPException(404, "仕訳が見つかりません")
    
    db.delete(journal)
    db.commit()
    
    return {"message": "仕訳を削除しました"}

@router.post("/generate-missing")
async def generate_missing_journals(
    db: Session = Depends(get_db)
):
    """Journalがない領収書に対してJournalを生成"""
    try:
        # すべての領収書を取得
        receipts = db.query(Receipt).all()
        logger.info(f"総領収書数: {len(receipts)}")
        
        # Journalがない領収書を特定
        missing_journal_receipts = []
        for receipt in receipts:
            journal_exists = db.query(JournalEntry).filter(
                JournalEntry.receipt_id == receipt.id
            ).first()
            
            if not journal_exists:
                missing_journal_receipts.append(receipt)
        
        logger.info(f"Journalがない領収書数: {len(missing_journal_receipts)}")
        
        if not missing_journal_receipts:
            return {
                "message": "すべての領収書にJournalが存在します",
                "receipts_checked": len(receipts),
                "journals_generated": 0
            }
        
        # Journal生成
        generator = JournalGenerator(db)
        generated_count = 0
        errors = []
        
        for receipt in missing_journal_receipts:
            try:
                logger.info(f"Processing receipt {receipt.id}: {receipt.vendor} - ¥{receipt.total}")
                
                # Journal生成
                journal_entries = generator.generate_journal_entries(receipt)
                
                for entry_data in journal_entries:
                    # フレーム時間を取得
                    time_ms = 0
                    if receipt.best_frame:
                        time_ms = receipt.best_frame.time_ms or 0
                    
                    journal_entry = JournalEntry(
                        receipt_id=entry_data.receipt_id,
                        video_id=entry_data.video_id,
                        time_ms=time_ms,
                        debit_account=entry_data.debit_account,
                        credit_account=entry_data.credit_account,
                        debit_amount=entry_data.debit_amount,
                        credit_amount=entry_data.credit_amount,
                        tax_account=entry_data.tax_account,
                        tax_amount=entry_data.tax_amount,
                        memo=entry_data.memo,
                        status='unconfirmed'
                    )
                    db.add(journal_entry)
                    generated_count += 1
                
                db.commit()
                
            except Exception as e:
                error_msg = f"Error processing receipt {receipt.id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                db.rollback()
                continue
        
        # 結果確認
        total_journals = db.query(JournalEntry).count()
        
        return {
            "message": f"{generated_count}件のJournalエントリを生成しました",
            "receipts_checked": len(receipts),
            "missing_journals_found": len(missing_journal_receipts),
            "journals_generated": generated_count,
            "total_journals": total_journals,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error(f"Journal生成エラー: {e}")
        raise HTTPException(500, f"Journal生成に失敗しました: {str(e)}")