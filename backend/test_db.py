#!/usr/bin/env python3
"""
データベース接続テストスクリプト
環境変数の設定を確認してSupabase接続をテスト
"""

import os
import sys
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

def test_supabase_connection():
    """Supabase接続URLを構築してテスト"""
    
    # Render環境をシミュレート
    os.environ["RENDER"] = "true"
    
    print("=== Supabase接続テスト ===")
    print(f"RENDER: {os.getenv('RENDER')}")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")
    print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'Not set')}")
    print(f"SUPABASE_PASSWORD: {'Set' if os.getenv('SUPABASE_PASSWORD') else 'Not set'}")
    
    # データベースモジュールをインポート
    try:
        from database import engine, DATABASE_URL
        print(f"\n構築されたURL: {DATABASE_URL[:50]}...")
        
        # 接続テスト
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("\n✅ データベース接続成功!")
            
            # PostgreSQLバージョン確認
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"PostgreSQL: {version[:50]}...")
            
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        print("\n解決方法:")
        print("1. Render Dashboardで以下の環境変数を設定:")
        print("   - DATABASE_URL: Supabase Pooler URL全体")
        print("   または")
        print("   - SUPABASE_URL: プロジェクトReference ID")
        print("   - SUPABASE_PASSWORD: データベースパスワード")
        print("\n2. Supabaseで確認:")
        print("   - Settings > Database > Connection Pooling")
        print("   - Mode: Transaction を選択")
        print("   - Connection string をコピー")
        return False
    
    return True

if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1)