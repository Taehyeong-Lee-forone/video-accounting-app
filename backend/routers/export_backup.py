from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io
from typing import Optional
from datetime import datetime

from database import get_db
from models import JournalEntry, Receipt, Video

router = APIRouter()

@router.get("/csv")
async def export_csv(
    video_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """CSV エクスポート"""
    
    # クエリ構築
    query = db.query(
        JournalEntry,
        Receipt,
        Video
    ).join(
        Receipt, JournalEntry.receipt_id == Receipt.id
    ).join(
        Video, JournalEntry.video_id == Video.id
    )
    
    if video_id:
        query = query.filter(JournalEntry.video_id == video_id)
    if status:
        query = query.filter(JournalEntry.status == status)
    if start_date:
        query = query.filter(Receipt.issue_date >= start_date)
    if end_date:
        query = query.filter(Receipt.issue_date <= end_date)
    
    results = query.all()
    
    # CSV生成
    output = io.StringIO()
    writer = csv.writer(output)
    
    # ヘッダー
    writer.writerow([
        '仕訳ID',
        '動画ID',
        '領収書ID',
        '時刻(ms)',
        'ステータス',
        'ベンダー',
        '発行日',
        '合計金額',
        '税抜金額',
        '消費税',
        '税率',
        '借方科目',
        '借方金額',
        '貸方科目',
        '貸方金額',
        'メモ',
        '承認者',
        '承認日時'
    ])
    
    # データ行
    for journal, receipt, video in results:
        writer.writerow([
            journal.id,
            video.id,
            receipt.id,
            journal.time_ms,
            journal.status,
            receipt.vendor,
            receipt.issue_date.strftime('%Y-%m-%d') if receipt.issue_date else '',
            receipt.total,
            receipt.subtotal,
            receipt.tax,
            f"{int(receipt.tax_rate * 100)}%" if receipt.tax_rate else '',
            journal.debit_account,
            journal.debit_amount,
            journal.credit_account,
            journal.credit_amount,
            journal.memo,
            journal.confirmed_by,
            journal.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if journal.confirmed_at else ''
        ])
    
    output.seek(0)
    
    # ファイル名生成
    filename = f"journal_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )