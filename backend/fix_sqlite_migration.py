#!/usr/bin/env python3
"""
SQLiteデータベースのuser_idカラム追加修正スクリプト
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_column_if_not_exists(conn, table, column, column_type):
    """カラムが存在しない場合のみ追加"""
    cur = conn.cursor()
    
    # カラム情報取得
    cur.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cur.fetchall()]
    
    if column not in columns:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            conn.commit()
            logger.info(f"✓ Added {column} to {table}")
        except sqlite3.OperationalError as e:
            logger.warning(f"⚠ Could not add {column} to {table}: {e}")
    else:
        logger.info(f"✓ {column} already exists in {table}")

def main():
    """メイン処理"""
    conn = sqlite3.connect('video_accounting.db')
    
    try:
        # user_idカラム追加
        add_column_if_not_exists(conn, 'videos', 'user_id', 'INTEGER')
        add_column_if_not_exists(conn, 'videos', 'cloud_url', 'VARCHAR(500)')
        add_column_if_not_exists(conn, 'videos', 'file_size_mb', 'REAL')
        add_column_if_not_exists(conn, 'receipts', 'user_id', 'INTEGER')
        add_column_if_not_exists(conn, 'journal_entries', 'user_id', 'INTEGER')
        
        # 既存データをadmin (user_id=1)に割り当て
        cur = conn.cursor()
        
        # Admin userが存在するか確認
        cur.execute("SELECT id FROM users WHERE username='admin'")
        admin = cur.fetchone()
        
        if admin:
            admin_id = admin[0]
            
            # 既存データ更新
            cur.execute("UPDATE videos SET user_id=? WHERE user_id IS NULL", (admin_id,))
            logger.info(f"✓ Updated {cur.rowcount} videos with admin user")
            
            cur.execute("UPDATE receipts SET user_id=? WHERE user_id IS NULL", (admin_id,))
            logger.info(f"✓ Updated {cur.rowcount} receipts with admin user")
            
            cur.execute("UPDATE journal_entries SET user_id=? WHERE user_id IS NULL", (admin_id,))
            logger.info(f"✓ Updated {cur.rowcount} journal entries with admin user")
            
            conn.commit()
        
        # インデックス作成
        try:
            cur.execute("CREATE INDEX idx_video_user ON videos(user_id)")
            logger.info("✓ Created index on videos.user_id")
        except:
            pass
            
        try:
            cur.execute("CREATE INDEX idx_receipt_user ON receipts(user_id)")
            logger.info("✓ Created index on receipts.user_id")
        except:
            pass
            
        try:
            cur.execute("CREATE INDEX idx_journal_user ON journal_entries(user_id)")
            logger.info("✓ Created index on journal_entries.user_id")
        except:
            pass
        
        logger.info("\n✅ SQLite migration completed successfully!")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()