#!/usr/bin/env python3
"""
既存の領収書に対して不足しているJournalEntriesを生成するスクリプト
プロダクション環境で実行して、JournalがないReceiptに対してJournalを生成する
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import Receipt, JournalEntry, Video
from services.journal_generator import JournalGenerator
from sqlalchemy import and_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_missing_journals():
    """Journalがない領収書を検索してJournalを生成"""
    db = next(get_db())
    
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
            logger.info("すべての領収書にJournalが存在します")
            return
        
        # Journal生成
        generator = JournalGenerator(db)
        generated_count = 0
        
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
                    logger.info(f"  → Journal created: 借方={entry_data.debit_account}, 貸方={entry_data.credit_account}")
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Error processing receipt {receipt.id}: {e}")
                db.rollback()
                continue
        
        logger.info(f"生成完了: {generated_count}件のJournalエントリを作成")
        
        # 結果確認
        total_journals = db.query(JournalEntry).count()
        logger.info(f"総Journalエントリ数: {total_journals}")
        
    except Exception as e:
        logger.error(f"エラー発生: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("=== Journal生成スクリプト開始 ===")
    generate_missing_journals()
    logger.info("=== 完了 ===")