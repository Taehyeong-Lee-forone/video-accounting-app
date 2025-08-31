#!/usr/bin/env python3
"""
journal_entriesテーブルに不足しているカラムを追加
"""
from sqlalchemy import create_engine, text

# Supabase接続URL
DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("不足カラムの追加")
print("="*50)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # journal_entriesテーブルのカラム確認
        print("\n2. journal_entriesテーブルのカラム確認...")
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'journal_entries'
            ORDER BY ordinal_position
        """))
        
        existing_columns = [row[0] for row in result]
        print(f"   既存カラム: {', '.join(existing_columns)}")
        
        # 必要なカラムのリスト（models.pyから）
        required_columns = {
            'time_ms': 'INTEGER',
            'debit_account': 'VARCHAR(100)',
            'credit_account': 'VARCHAR(100)',
            'debit_amount': 'FLOAT',
            'credit_amount': 'FLOAT',
            'tax_account': 'VARCHAR(100)',
            'tax_amount': 'FLOAT',
            'memo': 'TEXT',
            'status': 'VARCHAR(20)',
            'confirmed_by': 'VARCHAR(100)',
            'confirmed_at': 'TIMESTAMP WITH TIME ZONE',
            'created_at': 'TIMESTAMP WITH TIME ZONE',
            'updated_at': 'TIMESTAMP WITH TIME ZONE'
        }
        
        # 不足しているカラムを追加
        print("\n3. 不足カラムを追加中...")
        for column_name, data_type in required_columns.items():
            if column_name not in existing_columns:
                print(f"   - {column_name}を追加中...")
                
                # デフォルト値を設定
                default_clause = ""
                if column_name == 'status':
                    default_clause = " DEFAULT 'unconfirmed'"
                elif column_name == 'created_at' or column_name == 'updated_at':
                    default_clause = " DEFAULT CURRENT_TIMESTAMP"
                elif 'amount' in column_name:
                    default_clause = " DEFAULT 0"
                elif column_name == 'time_ms':
                    default_clause = " DEFAULT 0"
                
                sql = f"ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS {column_name} {data_type}{default_clause}"
                conn.execute(text(sql))
                print(f"     ✅ {column_name}追加完了")
        
        # 最終確認
        print("\n4. 最終的なjournal_entriesテーブル構造:")
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'journal_entries'
            ORDER BY ordinal_position
        """))
        
        for row in result:
            print(f"   - {row[0]}: {row[1]}")
    
    print("\n" + "="*50)
    print("✅ カラム追加完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()
