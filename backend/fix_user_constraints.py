#!/usr/bin/env python3
"""
すべてのテーブルのuser_id外部キー制約を解決
"""
from sqlalchemy import create_engine, text

# Supabase接続URL
DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("外部キー制約の解決")
print("="*50)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # 外部キー制約を一時的に無効化
        print("\n2. 外部キー制約を一時的に無効化...")
        conn.execute(text("SET session_replication_role = 'replica'"))
        
        # すべてのuser_idをNULLに設定
        print("\n3. user_idをNULLに設定中...")
        
        # videos
        result = conn.execute(text("UPDATE videos SET user_id = NULL WHERE user_id IS NOT NULL"))
        print(f"   - videos: {result.rowcount}行更新")
        
        # receipts
        result = conn.execute(text("UPDATE receipts SET user_id = NULL WHERE user_id IS NOT NULL"))
        print(f"   - receipts: {result.rowcount}行更新")
        
        # journal_entries
        result = conn.execute(text("UPDATE journal_entries SET user_id = NULL WHERE user_id IS NOT NULL"))
        print(f"   - journal_entries: {result.rowcount}行更新")
        
        # 外部キー制約を再有効化
        print("\n4. 外部キー制約を再有効化...")
        conn.execute(text("SET session_replication_role = 'origin'"))
        
        # 現在の状態確認
        print("\n5. 現在の状態確認:")
        
        # 各テーブルのレコード数確認
        for table in ['videos', 'frames', 'receipts', 'journal_entries']:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   - {table}: {count}レコード")
    
    print("\n" + "="*50)
    print("✅ 外部キー制約の解決完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()