#!/usr/bin/env python3
"""
PostgreSQL enum タイプの現在状態を確認するスクリプト
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def check_enum_status():
    """データベースのenum状態をチェック"""
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URLが設定されていません")
        return False
    
    try:
        engine = create_engine(DATABASE_URL)
        
        print("🔍 PostgreSQL enum タイプの状態をチェック中...")
        
        # video_statusの現在の値を確認
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'video_status'
                ORDER BY enumsortorder;
            """))
            
            video_status_values = [row[0] for row in result.fetchall()]
            print(f"📋 現在のvideo_status enum値: {video_status_values}")
            
            # videosテーブルのstatusカラムの実際の値を確認
            result = conn.execute(text("""
                SELECT DISTINCT status, COUNT(*) 
                FROM videos 
                GROUP BY status 
                ORDER BY status;
            """))
            
            actual_values = result.fetchall()
            print(f"📊 videosテーブルの実際のstatus値:")
            for value, count in actual_values:
                print(f"   - '{value}': {count}件")
            
            # 問題の確認
            if 'QUEUED' in video_status_values:
                print("⚠️  enum定義に'QUEUED'（大文字）が存在します")
            if 'queued' in video_status_values:
                print("✅ enum定義に'queued'（小文字）が存在します")
            
            return True
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    success = check_enum_status()
    sys.exit(0 if success else 1)