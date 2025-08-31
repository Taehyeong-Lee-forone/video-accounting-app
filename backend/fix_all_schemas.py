#!/usr/bin/env python3
"""
すべてのテーブルの不足カラムを追加
"""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("完全スキーマ修正")
print("="*50)

engine = create_engine(DATABASE_URL)

# Receiptsテーブルに必要なカラム
receipts_columns = {
    'currency': "VARCHAR(3) DEFAULT 'JPY'",
    'tax_rate': "FLOAT DEFAULT 0.1",
    'duplicate_of_id': 'INTEGER',
    'normalized_text_hash': 'VARCHAR(64)'
}

# Framesテーブルに必要なカラム 
frames_columns = {
    'frame_score': 'FLOAT',
    'frame_path': 'VARCHAR(500)',
    'is_best': 'BOOLEAN DEFAULT FALSE'
}

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # Receiptsテーブル修正
        print("\n2. receiptsテーブル修正...")
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'receipts'
        """))
        existing = [row[0] for row in result]
        
        for col_name, col_def in receipts_columns.items():
            if col_name not in existing:
                print(f"   - {col_name}追加中...")
                conn.execute(text(f"ALTER TABLE receipts ADD COLUMN IF NOT EXISTS {col_name} {col_def}"))
                print(f"     ✅ 完了")
        
        # Framesテーブル修正
        print("\n3. framesテーブル修正...")
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'frames'
        """))
        existing = [row[0] for row in result]
        
        for col_name, col_def in frames_columns.items():
            if col_name not in existing:
                print(f"   - {col_name}追加中...")
                conn.execute(text(f"ALTER TABLE frames ADD COLUMN IF NOT EXISTS {col_name} {col_def}"))
                print(f"     ✅ 完了")
        
        # 最終確認
        print("\n4. レコード数確認:")
        for table in ['videos', 'frames', 'receipts', 'journal_entries']:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   - {table}: {count}レコード")
    
    print("\n" + "="*50)
    print("✅ 完全スキーマ修正完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()
