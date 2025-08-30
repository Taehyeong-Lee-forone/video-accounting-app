#!/usr/bin/env python3
"""
データベーステーブル確認スクリプト
既存のテーブルとインデックスを確認
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text, inspect

load_dotenv()

# DATABASE_URLを設定（テスト用）
if len(sys.argv) > 1:
    os.environ["DATABASE_URL"] = sys.argv[1]

from database import engine

def check_database():
    """データベースの状態を確認"""
    try:
        inspector = inspect(engine)
        
        # テーブル一覧
        tables = inspector.get_table_names()
        print(f"既存のテーブル: {tables}")
        
        # 各テーブルのインデックスを確認
        for table in tables:
            indexes = inspector.get_indexes(table)
            if indexes:
                print(f"\n{table}テーブルのインデックス:")
                for idx in indexes:
                    print(f"  - {idx['name']}")
        
        # 接続テスト
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM videos"))
            count = result.scalar()
            print(f"\nvideosテーブルのレコード数: {count}")
            
        print("\n✅ データベース接続成功")
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    check_database()