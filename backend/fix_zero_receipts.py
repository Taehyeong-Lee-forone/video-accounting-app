"""
0원 영수증 재처리 스크립트
"""

import sqlite3
from utils.receipt_parser import ReceiptParser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_zero_receipts():
    """
    # 0円レシートを再解析して修正
    """
    conn = sqlite3.connect('video_accounting.db')
    cursor = conn.cursor()
    
    # 0원 영수증 조회
    cursor.execute("""
        SELECT r.id, r.vendor, f.ocr_text, f.frame_path
        FROM receipts r
        LEFT JOIN frames f ON r.best_frame_id = f.id
        WHERE (r.total = 0 OR r.total IS NULL) 
        AND f.ocr_text IS NOT NULL
        AND LENGTH(f.ocr_text) > 50
    """)
    
    zero_receipts = cursor.fetchall()
    logger.info(f"0원 영수증 {len(zero_receipts)}개 발견")
    
    parser = ReceiptParser()
    fixed_count = 0
    
    for receipt_id, vendor, ocr_text, frame_path in zero_receipts:
        if not ocr_text:
            continue
            
        # OCR 텍스트 재파싱
        result = parser.parse_receipt(ocr_text)
        
        if result['total'] and result['total'] > 0:
            # 업데이트
            cursor.execute("""
                UPDATE receipts 
                SET total = ?, subtotal = ?, tax = ?
                WHERE id = ?
            """, (result['total'], result['subtotal'], result['tax'], receipt_id))
            
            fixed_count += 1
            logger.info(f"수정됨: Receipt #{receipt_id} ({vendor}) - Total: {result['total']}円")
        else:
            logger.warning(f"파싱 실패: Receipt #{receipt_id} ({vendor}) - {frame_path}")
            # OCR 텍스트 일부 출력
            first_lines = '\n'.join(ocr_text.split('\n')[:5])
            logger.debug(f"  OCR 텍스트: {first_lines}...")
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ 총 {fixed_count}개 영수증 수정 완료")
    return fixed_count

if __name__ == "__main__":
    fix_zero_receipts()