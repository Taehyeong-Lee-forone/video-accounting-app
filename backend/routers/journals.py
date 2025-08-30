from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import JournalEntry
from schemas import JournalEntryResponse, JournalEntryUpdate, JournalConfirm

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