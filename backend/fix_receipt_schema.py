#!/usr/bin/env python3
"""
receiptsとjournal_entriesテーブルにuser_idカラムを追加
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Supabase接続URL
DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("テーブルスキーマ修正")
print("="*50)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # user_idカラムが存在するか確認
        print("\n2. receiptsテーブルのカラム確認...")
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'receipts' 
            AND column_name = 'user_id'
        """))
        
        if result.rowcount == 0:
            print("   user_idカラムが存在しません")
            
            # user_idカラムを追加
            print("\n3. user_idカラムを追加中...")
            conn.execute(text("""
                ALTER TABLE receipts 
                ADD COLUMN IF NOT EXISTS user_id INTEGER
            """))
            print("   ✅ user_idカラムを追加しました")
        else:
            print("   ✅ user_idカラムは既に存在します")
        
        # journal_entriesテーブルも修正
        print("\n4. journal_entriesテーブルのカラム確認...")
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'journal_entries' 
            AND column_name = 'user_id'
        """))
        
        if result.rowcount == 0:
            print("   user_idカラムが存在しません")
            
            # user_idカラムを追加
            print("\n5. journal_entriesにuser_idカラムを追加中...")
            conn.execute(text("""
                ALTER TABLE journal_entries 
                ADD COLUMN IF NOT EXISTS user_id INTEGER
            """))
            print("   ✅ user_idカラムを追加しました")
        else:
            print("   ✅ user_idカラムは既に存在します")
        
        # 現在のスキーマ確認
        print("\n6. 現在のテーブル構造:")
        print("\n   receiptsテーブル:")
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'receipts'
            AND column_name IN ('id', 'user_id', 'video_id')
            ORDER BY ordinal_position
        """))
        for row in result:
            print(f"     - {row[0]}: {row[1]}")
            
        print("\n   journal_entriesテーブル:")
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'journal_entries'
            AND column_name IN ('id', 'user_id', 'video_id', 'receipt_id')
            ORDER BY ordinal_position
        """))
        for row in result:
            print(f"     - {row[0]}: {row[1]}")
    
    print("\n" + "="*50)
    print("✅ スキーマ修正完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()