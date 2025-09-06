#!/usr/bin/env python3
"""
データベースマイグレーションスクリプト
transaction_dateカラムをjournal_entriesテーブルに追加
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """SQLiteデータベースにtransaction_dateカラムを追加"""
    
    db_path = "video_accounting.db"
    
    if not os.path.exists(db_path):
        print(f"データベースファイルが見つかりません: {db_path}")
        return False
    
    try:
        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 現在のテーブル構造を確認
        cursor.execute("PRAGMA table_info(journal_entries)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("現在のカラム:", column_names)
        
        # transaction_dateカラムが存在しない場合のみ追加
        if 'transaction_date' not in column_names:
            print("transaction_dateカラムを追加中...")
            
            # SQLiteは ALTER TABLE ADD COLUMN で NOT NULL制約を直接追加できないため、
            # まずNULL許可で追加し、既存データを更新してからNOT NULLにする
            
            # 1. カラムを追加（NULL許可）
            cursor.execute("""
                ALTER TABLE journal_entries 
                ADD COLUMN transaction_date DATE
            """)
            
            # 2. 既存のレコードを更新（issue_dateまたは現在の日付を使用）
            cursor.execute("""
                UPDATE journal_entries 
                SET transaction_date = DATE(
                    COALESCE(
                        (SELECT issue_date FROM receipts WHERE receipts.id = journal_entries.receipt_id),
                        CURRENT_DATE
                    )
                )
                WHERE transaction_date IS NULL
            """)
            
            conn.commit()
            print("✅ transaction_dateカラムを正常に追加しました")
            
            # 追加後の確認
            cursor.execute("PRAGMA table_info(journal_entries)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            print("更新後のカラム:", column_names)
            
        else:
            print("transaction_dateカラムは既に存在します")
        
        # テストクエリ実行
        cursor.execute("SELECT COUNT(*) FROM journal_entries WHERE transaction_date IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"transaction_dateが設定されているレコード数: {count}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"データベースエラー: {e}")
        return False
    except Exception as e:
        print(f"予期しないエラー: {e}")
        return False

if __name__ == "__main__":
    print("データベースマイグレーション開始...")
    success = migrate_database()
    
    if success:
        print("✅ マイグレーション完了")
    else:
        print("❌ マイグレーション失敗")