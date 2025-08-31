#!/usr/bin/env python3
"""
videosテーブルにuser_idカラムを追加
"""
from sqlalchemy import create_engine, text

# Supabase接続URL
DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("Videosテーブルにuser_idカラム追加")
print("="*50)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # user_idカラムが存在するか確認
        print("\n2. videosテーブルのカラム確認...")
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'videos' 
            AND column_name = 'user_id'
        """))
        
        if result.rowcount == 0:
            print("   user_idカラムが存在しません")
            
            # user_idカラムを追加
            print("\n3. user_idカラムを追加中...")
            conn.execute(text("""
                ALTER TABLE videos 
                ADD COLUMN IF NOT EXISTS user_id INTEGER
            """))
            print("   ✅ user_idカラムを追加しました")
        else:
            print("   ✅ user_idカラムは既に存在します")
        
        # 現在のスキーマ確認
        print("\n4. 現在のvideosテーブル構造:")
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'videos'
            AND column_name IN ('id', 'user_id', 'filename', 'status')
            ORDER BY ordinal_position
        """))
        
        for row in result:
            print(f"   - {row[0]}: {row[1]}")
    
    print("\n" + "="*50)
    print("✅ 完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()