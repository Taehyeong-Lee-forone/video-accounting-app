from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io
from typing import Optional
from datetime import datetime
from enum import Enum

from database import get_db
from models import JournalEntry, Receipt, Video

router = APIRouter()

class ExportFormat(str, Enum):
    STANDARD = "standard"  # 現在形式
    YAYOI = "yayoi"  # 弥生会計
    FREEE = "freee"  # freee
    MF = "moneyforward"  # MoneyForward

@router.get("/csv")
async def export_csv(
    video_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    format: ExportFormat = Query(ExportFormat.STANDARD),
    db: Session = Depends(get_db)
):
    """改善されたCSVエクスポート - 各会計ソフト対応"""
    
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
    
    if format == ExportFormat.YAYOI:
        # 弥生会計形式
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow([
            '伝票日付', '伝票番号', '借方科目', '借方補助', '借方税区分', 
            '借方金額', '貸方科目', '貸方補助', '貸方税区分', '貸方金額', 
            '摘要', '証憑番号'
        ])
        
        for journal, receipt, video in results:
            # 税込金額と税抜金額を分けて出力
            writer.writerow([
                receipt.issue_date.strftime('%Y/%m/%d') if receipt.issue_date else '',
                f"R{receipt.id:06d}",  # 領収書番号
                journal.debit_account or '経費',
                '',  # 補助科目
                '課税仕入 10%' if receipt.tax_rate == 0.10 else '課税仕入 8%',
                f"{int(journal.debit_amount):,}" if journal.debit_amount else '0',
                journal.credit_account or '現金',
                '',  # 補助科目
                '',  # 貸方は非課税
                f"{int(journal.credit_amount):,}" if journal.credit_amount else '0',
                f"{receipt.vendor} - {journal.memo}" if receipt.vendor else journal.memo,
                f"V{video.id:03d}R{receipt.id:06d}"  # 証憑番号
            ])
    
    elif format == ExportFormat.FREEE:
        # freee形式
        writer = csv.writer(output)
        writer.writerow([
            '発生日', '勘定科目', '税区分', '金額', '取引先', 
            '品目', '部門', 'メモタグ', '備考', '証憑ID'
        ])
        
        for journal, receipt, video in results:
            writer.writerow([
                receipt.issue_date.strftime('%Y-%m-%d') if receipt.issue_date else '',
                journal.debit_account or '経費',
                '課税仕入10%' if receipt.tax_rate == 0.10 else '課税仕入8%',
                int(receipt.total) if receipt.total else 0,
                receipt.vendor or '',
                journal.memo or '',
                '',  # 部門
                '',  # メモタグ
                f"動画{video.id}より",
                f"R{receipt.id:06d}"
            ])
    
    elif format == ExportFormat.MF:
        # MoneyForward形式
        writer = csv.writer(output)
        writer.writerow([
            '取引日', '摘要', '借方勘定科目', '借方金額', 
            '貸方勘定科目', '貸方金額', '税率', '消費税額', 'タグ'
        ])
        
        for journal, receipt, video in results:
            tax_rate_str = '10%' if receipt.tax_rate == 0.10 else '8%' if receipt.tax_rate == 0.08 else '0%'
            writer.writerow([
                receipt.issue_date.strftime('%Y/%m/%d') if receipt.issue_date else '',
                f"{receipt.vendor} {journal.memo}" if receipt.vendor else journal.memo,
                journal.debit_account or '経費',
                int(journal.debit_amount) if journal.debit_amount else 0,
                journal.credit_account or '現金',
                int(journal.credit_amount) if journal.credit_amount else 0,
                tax_rate_str,
                int(receipt.tax) if receipt.tax else 0,
                f"領収書{receipt.id}"
            ])
    
    else:
        # 標準形式（現在の形式を改善）
        writer = csv.writer(output)
        writer.writerow([
            '日付', '取引先', '摘要', '借方科目', '借方金額',
            '貸方科目', '貸方金額', '税率', '消費税', 'ステータス'
        ])
        
        for journal, receipt, video in results:
            writer.writerow([
                receipt.issue_date.strftime('%Y-%m-%d') if receipt.issue_date else '',
                receipt.vendor or '',
                journal.memo or '',
                journal.debit_account or '',
                f"{int(journal.debit_amount):,}" if journal.debit_amount else '0',
                journal.credit_account or '',
                f"{int(journal.credit_amount):,}" if journal.credit_amount else '0',
                f"{int(receipt.tax_rate * 100)}%" if receipt.tax_rate else '',
                f"{int(receipt.tax):,}" if receipt.tax else '0',
                '確認済' if journal.status == 'confirmed' else '未確認'
            ])
    
    output.seek(0)
    
    # ファイル名生成（形式名を含む）
    format_suffix = f"_{format.value}" if format != ExportFormat.STANDARD else ""
    filename = f"journal_export{format_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # BOM付きUTF-8
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8-sig"
        }
    )

@router.get("/csv/formats")
async def get_export_formats():
    """利用可能なエクスポート形式一覧"""
    return {
        "formats": [
            {
                "value": "standard",
                "label": "標準形式",
                "description": "シンプルな汎用形式"
            },
            {
                "value": "yayoi",
                "label": "弥生会計",
                "description": "弥生会計インポート対応形式"
            },
            {
                "value": "freee",
                "label": "freee",
                "description": "クラウド会計freee対応形式"
            },
            {
                "value": "moneyforward",
                "label": "MoneyForward",
                "description": "マネーフォワード対応形式"
            }
        ]
    }