#!/usr/bin/env python3
"""
Supabaseデータベース初期化スクリプト
Render環境でのデータベース接続テストとテーブル作成
"""

import os
import sys
from dotenv import load_dotenv
import logging

# 環境変数を読み込む
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    """データベース接続をテスト"""
    try:
        # Render環境変数を設定してインポート
        if len(sys.argv) > 1 and sys.argv[1] == "--render":
            os.environ["RENDER"] = "true"
            logger.info("Render環境モードで実行")
        
        from database import engine, Base
        from sqlalchemy import text
        
        # 接続テスト
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"データベース接続成功: {version}")
            
            # テーブル作成
            logger.info("テーブルを作成中...")
            Base.metadata.create_all(bind=engine)
            logger.info("テーブル作成完了")
            
            # テーブル一覧を表示
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            logger.info(f"作成されたテーブル: {tables}")
            
        return True
        
    except Exception as e:
        logger.error(f"データベース接続エラー: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)