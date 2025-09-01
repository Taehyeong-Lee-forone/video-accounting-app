#!/usr/bin/env python3
"""
Render PostgreSQL データベース設定スクリプト
既存のSQLiteデータをRender PostgreSQLに移行する
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import json
from datetime import datetime
import ssl

load_dotenv()

# Render PostgreSQL接続情報
# Render Dashboardから取得した情報を設定
RENDER_DATABASE_URL = "postgresql://video_accounting_user:OGyXPOJCcPzwRJoXxFGlSVcCJBP6LNbG@dpg-cto3ltjqf0us73c9hfog-a.oregon-postgres.render.com/video_accounting_db"

def export_sqlite_data():
    """SQLiteからデータをエクスポート"""
    print("SQLiteデータベースからデータを読み込み中...")
    
    conn = sqlite3.connect('video_accounting.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    data = {}
    
    # Users
    cursor.execute("SELECT * FROM users")
    data['users'] = [dict(row) for row in cursor.fetchall()]
    print(f"  Users: {len(data['users'])}件")
    
    # Videos
    cursor.execute("SELECT * FROM videos")
    data['videos'] = [dict(row) for row in cursor.fetchall()]
    print(f"  Videos: {len(data['videos'])}件")
    
    # Frames
    cursor.execute("SELECT * FROM frames")
    data['frames'] = [dict(row) for row in cursor.fetchall()]
    print(f"  Frames: {len(data['frames'])}件")
    
    # Receipts
    cursor.execute("SELECT * FROM receipts")
    data['receipts'] = [dict(row) for row in cursor.fetchall()]
    print(f"  Receipts: {len(data['receipts'])}件")
    
    # Receipt History (テーブルが存在する場合のみ)
    try:
        cursor.execute("SELECT * FROM receipt_history")
        data['receipt_history'] = [dict(row) for row in cursor.fetchall()]
        print(f"  Receipt History: {len(data['receipt_history'])}件")
    except sqlite3.OperationalError:
        data['receipt_history'] = []
        print(f"  Receipt History: テーブルが存在しません")
    
    # Journal Entries
    cursor.execute("SELECT * FROM journal_entries")
    data['journal_entries'] = [dict(row) for row in cursor.fetchall()]
    print(f"  Journal Entries: {len(data['journal_entries'])}件")
    
    conn.close()
    return data

def create_postgresql_schema(conn):
    """PostgreSQLにテーブルを作成"""
    print("\nPostgreSQLテーブルを作成中...")
    
    cursor = conn.cursor()
    
    # 既存のテーブルを削除（開発用）
    cursor.execute("""
        DROP TABLE IF EXISTS journal_entries CASCADE;
        DROP TABLE IF EXISTS receipt_history CASCADE;
        DROP TABLE IF EXISTS receipts CASCADE;
        DROP TABLE IF EXISTS frames CASCADE;
        DROP TABLE IF EXISTS videos CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
    """)
    
    # Usersテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Videosテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500),
            file_url VARCHAR(500),
            storage_path VARCHAR(500),
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT FALSE,
            processing_progress INTEGER DEFAULT 0,
            total_frames INTEGER DEFAULT 0,
            fps FLOAT,
            duration FLOAT,
            status VARCHAR(50) DEFAULT 'pending',
            error_message TEXT,
            thumbnail_path VARCHAR(500),
            thumbnail_url VARCHAR(500)
        )
    """)
    
    # Framesテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS frames (
            id SERIAL PRIMARY KEY,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            frame_number INTEGER NOT NULL,
            timestamp FLOAT NOT NULL,
            file_path VARCHAR(500),
            file_url VARCHAR(500),
            storage_path VARCHAR(500),
            has_receipt BOOLEAN DEFAULT FALSE,
            confidence_score FLOAT,
            processing_status VARCHAR(50) DEFAULT 'pending',
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB
        )
    """)
    
    # Receiptsテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id SERIAL PRIMARY KEY,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            frame_id INTEGER REFERENCES frames(id) ON DELETE CASCADE,
            best_frame_id INTEGER REFERENCES frames(id),
            store_name VARCHAR(255),
            total_amount DECIMAL(10, 2),
            tax_amount DECIMAL(10, 2),
            date DATE,
            items JSONB,
            raw_text TEXT,
            confidence_score FLOAT,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB,
            payment_method VARCHAR(100),
            ai_analysis JSONB
        )
    """)
    
    # Receipt Historyテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipt_history (
            id SERIAL PRIMARY KEY,
            receipt_id INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
            frame_id INTEGER REFERENCES frames(id),
            store_name VARCHAR(255),
            total_amount DECIMAL(10, 2),
            tax_amount DECIMAL(10, 2),
            date DATE,
            items JSONB,
            raw_text TEXT,
            confidence_score FLOAT,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB
        )
    """)
    
    # Journal Entriesテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id SERIAL PRIMARY KEY,
            receipt_id INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            description TEXT,
            account_code VARCHAR(50),
            debit_account VARCHAR(255),
            credit_account VARCHAR(255),
            amount DECIMAL(12, 2) NOT NULL,
            tax_amount DECIMAL(10, 2),
            tax_rate DECIMAL(5, 2),
            memo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB
        )
    """)
    
    # インデックスを作成
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_frames_video_id ON frames(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_video_id ON receipts(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_journal_entries_video_id ON journal_entries(video_id)")
    
    conn.commit()
    print("テーブル作成完了")

def import_to_postgresql(conn, data):
    """PostgreSQLにデータをインポート"""
    print("\nPostgreSQLにデータをインポート中...")
    
    cursor = conn.cursor()
    
    # Users
    if data['users']:
        print("  Usersをインポート中...")
        for user in data['users']:
            cursor.execute("""
                INSERT INTO users (id, username, email, hashed_password, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                user['id'], user['username'], user['email'],
                user['hashed_password'], user.get('is_active', True),
                user.get('created_at', datetime.now())
            ))
    
    # Videos
    if data['videos']:
        print("  Videosをインポート中...")
        for video in data['videos']:
            cursor.execute("""
                INSERT INTO videos (
                    id, user_id, filename, file_path, file_url, storage_path,
                    uploaded_at, processed, processing_progress, total_frames,
                    fps, duration, status, error_message, thumbnail_path, thumbnail_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                video['id'], video.get('user_id'), video['filename'],
                video.get('file_path'), video.get('file_url'), video.get('storage_path'),
                video.get('uploaded_at', datetime.now()), video.get('processed', False),
                video.get('processing_progress', 0), video.get('total_frames', 0),
                video.get('fps'), video.get('duration'), video.get('status', 'pending'),
                video.get('error_message'), video.get('thumbnail_path'), video.get('thumbnail_url')
            ))
    
    # Frames
    if data['frames']:
        print("  Framesをインポート中...")
        for frame in data['frames']:
            metadata = frame.get('metadata')
            if metadata and isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = None
            
            cursor.execute("""
                INSERT INTO frames (
                    id, video_id, frame_number, timestamp, file_path, file_url,
                    storage_path, has_receipt, confidence_score, processing_status,
                    extracted_at, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                frame['id'], frame['video_id'], frame['frame_number'],
                frame['timestamp'], frame.get('file_path'), frame.get('file_url'),
                frame.get('storage_path'), frame.get('has_receipt', False),
                frame.get('confidence_score'), frame.get('processing_status', 'pending'),
                frame.get('extracted_at', datetime.now()),
                json.dumps(metadata) if metadata else None
            ))
    
    # Receipts
    if data['receipts']:
        print("  Receiptsをインポート中...")
        for receipt in data['receipts']:
            items = receipt.get('items')
            if items and isinstance(items, str):
                try:
                    items = json.loads(items)
                except:
                    items = None
            
            metadata = receipt.get('metadata')
            if metadata and isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = None
            
            ai_analysis = receipt.get('ai_analysis')
            if ai_analysis and isinstance(ai_analysis, str):
                try:
                    ai_analysis = json.loads(ai_analysis)
                except:
                    ai_analysis = None
            
            cursor.execute("""
                INSERT INTO receipts (
                    id, video_id, frame_id, best_frame_id, store_name,
                    total_amount, tax_amount, date, items, raw_text,
                    confidence_score, extracted_at, metadata, payment_method, ai_analysis
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                receipt['id'], receipt['video_id'], receipt.get('frame_id'),
                receipt.get('best_frame_id'), receipt.get('store_name'),
                receipt.get('total_amount'), receipt.get('tax_amount'),
                receipt.get('date'), json.dumps(items) if items else None,
                receipt.get('raw_text'), receipt.get('confidence_score'),
                receipt.get('extracted_at', datetime.now()),
                json.dumps(metadata) if metadata else None,
                receipt.get('payment_method'), json.dumps(ai_analysis) if ai_analysis else None
            ))
    
    # Journal Entries
    if data['journal_entries']:
        print("  Journal Entriesをインポート中...")
        for entry in data['journal_entries']:
            metadata = entry.get('metadata')
            if metadata and isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = None
            
            cursor.execute("""
                INSERT INTO journal_entries (
                    id, receipt_id, video_id, date, description, account_code,
                    debit_account, credit_account, amount, tax_amount, tax_rate,
                    memo, created_at, updated_at, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                entry['id'], entry.get('receipt_id'), entry.get('video_id'),
                entry['date'], entry.get('description'), entry.get('account_code'),
                entry.get('debit_account'), entry.get('credit_account'),
                entry['amount'], entry.get('tax_amount'), entry.get('tax_rate'),
                entry.get('memo'), entry.get('created_at', datetime.now()),
                entry.get('updated_at', datetime.now()),
                json.dumps(metadata) if metadata else None
            ))
    
    # シーケンスをリセット
    cursor.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")
    cursor.execute("SELECT setval('videos_id_seq', (SELECT MAX(id) FROM videos))")
    cursor.execute("SELECT setval('frames_id_seq', (SELECT MAX(id) FROM frames))")
    cursor.execute("SELECT setval('receipts_id_seq', (SELECT MAX(id) FROM receipts))")
    cursor.execute("SELECT setval('journal_entries_id_seq', (SELECT MAX(id) FROM journal_entries))")
    
    conn.commit()
    print("データインポート完了")

def main():
    print("=" * 60)
    print("Render PostgreSQL データベース移行スクリプト")
    print("=" * 60)
    
    # SQLiteデータをエクスポート
    data = export_sqlite_data()
    
    # PostgreSQLに接続
    print(f"\nPostgreSQLに接続中...")
    print(f"URL: {RENDER_DATABASE_URL.split('@')[1].split('/')[0]}")
    
    try:
        # SSL設定を追加
        conn = psycopg2.connect(
            RENDER_DATABASE_URL,
            sslmode='require',
            connect_timeout=30
        )
        print("接続成功")
        
        # スキーマを作成
        create_postgresql_schema(conn)
        
        # データをインポート
        import_to_postgresql(conn, data)
        
        # 統計を表示
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM videos")
        video_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM receipts")
        receipt_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM journal_entries")
        journal_count = cursor.fetchone()[0]
        
        print("\n" + "=" * 60)
        print("移行完了!")
        print(f"  Videos: {video_count}件")
        print(f"  Receipts: {receipt_count}件")
        print(f"  Journal Entries: {journal_count}件")
        print("=" * 60)
        
        # .envファイルを更新
        print("\n.envファイルを更新してください:")
        print(f"DATABASE_URL={RENDER_DATABASE_URL}")
        
        conn.close()
        
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()