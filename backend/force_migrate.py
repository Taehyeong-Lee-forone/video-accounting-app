"""
緊急マイグレーションスクリプト
User モデルを読み込まずに直接SQLでカラムを追加
"""
import os
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース接続設定
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Render環境でのデフォルト設定
    DATABASE_URL = "postgresql://video_accounting_app_user:P21G9zyHJvRjd9EcO4MnhD3tFa7HHWUD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

# SQLAlchemyエンジン作成
engine = create_engine(DATABASE_URL)

def force_add_columns():
    """強制的にカラムを追加"""
    
    with engine.connect() as conn:
        try:
            # PostgreSQL用のカラム追加
            logger.info("PostgreSQL: reset_tokenカラムの追加を試みます...")
            
            # reset_tokenカラムを追加
            try:
                conn.execute(text("""
                    ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)
                """))
                conn.commit()
                logger.info("✅ reset_tokenカラムを追加しました")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️ reset_tokenカラムは既に存在します")
                else:
                    logger.error(f"❌ reset_tokenカラム追加エラー: {e}")
            
            # reset_token_expiresカラムを追加
            try:
                conn.execute(text("""
                    ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP WITH TIME ZONE
                """))
                conn.commit()
                logger.info("✅ reset_token_expiresカラムを追加しました")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("ℹ️ reset_token_expiresカラムは既に存在します")
                else:
                    logger.error(f"❌ reset_token_expiresカラム追加エラー: {e}")
            
            # カラム情報を確認
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('reset_token', 'reset_token_expires')
            """))
            
            columns = result.fetchall()
            logger.info("現在のカラム状態:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
            
            if len(columns) == 2:
                logger.info("✅ 必要なカラムがすべて存在します")
                return True
            else:
                logger.error("❌ 一部のカラムが不足しています")
                return False
                
        except Exception as e:
            logger.error(f"マイグレーションエラー: {e}")
            return False

if __name__ == "__main__":
    logger.info("=== 緊急マイグレーション開始 ===")
    if force_add_columns():
        logger.info("✅ マイグレーション成功")
    else:
        logger.error("❌ マイグレーション失敗")