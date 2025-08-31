#!/usr/bin/env python3
"""
videos テーブルに不足しているカラムを追加
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Supabase接続URL
DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("Videos テーブル カラム追加")
print("="*50)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # 現在のvideosテーブル構造を確認
        print("\n2. 現在のvideosテーブル構造確認...")
        check_columns = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'videos'
        ORDER BY ordinal_position;
        """
        result = conn.execute(text(check_columns))
        existing_columns = {row[0]: row[1] for row in result}
        
        print("   既存カラム:")
        for col, dtype in existing_columns.items():
            print(f"   - {col}: {dtype}")
        
        # 必要なカラムのリスト
        required_columns = {
            'cloud_url': 'VARCHAR(500)',
            'local_path': 'VARCHAR(500)',
            'thumbnail_path': 'VARCHAR(500)',
            'file_size_mb': 'FLOAT',
            'duration_ms': 'INTEGER',
            'original_filename': 'VARCHAR(255)',
            'file_size': 'BIGINT',
            'duration': 'FLOAT',
            'fps': 'FLOAT',
            'width': 'INTEGER',
            'height': 'INTEGER',
            'processing_started_at': 'TIMESTAMP',
            'processing_completed_at': 'TIMESTAMP'
        }
        
        # 不足しているカラムを追加
        print("\n3. 不足カラムを追加中...")
        added_columns = []
        
        for column, dtype in required_columns.items():
            if column not in existing_columns:
                try:
                    # PostgreSQL用のデータ型に変換
                    pg_dtype = dtype.replace('VARCHAR', 'VARCHAR').replace('FLOAT', 'REAL')
                    
                    alter_sql = f"ALTER TABLE videos ADD COLUMN IF NOT EXISTS {column} {pg_dtype}"
                    conn.execute(text(alter_sql))
                    added_columns.append(column)
                    print(f"   ✅ {column} カラム追加")
                except Exception as e:
                    print(f"   ⚠️ {column} カラム追加エラー: {e}")
        
        if not added_columns:
            print("   ℹ️ 追加するカラムはありません")
        
        # statusカラムのデフォルト値設定
        print("\n4. statusカラムのデフォルト値設定...")
        try:
            conn.execute(text("""
                ALTER TABLE videos 
                ALTER COLUMN status SET DEFAULT 'pending'
            """))
            print("   ✅ statusカラムのデフォルト値設定完了")
        except:
            print("   ℹ️ 既に設定済み")
        
        # 最終的なテーブル構造確認
        print("\n5. 更新後のテーブル構造確認...")
        result = conn.execute(text(check_columns))
        final_columns = [row[0] for row in result]
        
        print("   最終カラムリスト:")
        for col in final_columns:
            print(f"   - {col}")
        
        print(f"\n   合計カラム数: {len(final_columns)}")
    
    print("\n" + "="*50)
    print("✅ カラム追加完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()