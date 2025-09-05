import sys
sys.path.append('backend')
from database import get_db
from models import Video, Receipt, JournalEntry

# DB 세션
db = next(get_db())

# 최근 비디오의 영수증과 journal 매핑 확인
latest_video = db.query(Video).order_by(Video.id.desc()).first()

if latest_video:
    print(f'=== Video {latest_video.id} 데이터 확인 ===')
    
    # 영수증 목록
    receipts = db.query(Receipt).filter(Receipt.video_id == latest_video.id).all()
    print(f'\n영수증 개수: {len(receipts)}')
    for r in receipts[:5]:
        print(f'  Receipt ID: {r.id}, Vendor: {r.vendor}, Total: {r.total}')
    
    # Journal 목록
    journals = db.query(JournalEntry).filter(JournalEntry.video_id == latest_video.id).all()
    print(f'\nJournal 개수: {len(journals)}')
    for j in journals[:5]:
        print(f'  Journal ID: {j.id}, Receipt ID: {j.receipt_id}, 借方: {j.debit_account}')
    
    # 매핑 확인
    print('\n=== Receipt-Journal 매핑 ===')
    for r in receipts[:5]:
        journal = db.query(JournalEntry).filter(JournalEntry.receipt_id == r.id).first()
        if journal:
            print(f'  Receipt {r.id} → Journal {journal.id} ✓')
        else:
            print(f'  Receipt {r.id} → Journal 없음 ✗')

db.close()
