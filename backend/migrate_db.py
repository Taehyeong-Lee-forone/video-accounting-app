"""
データベースマイグレーションスクリプト
Userテーブルにreset_token, reset_token_expiresカラムを追加
"""
from sqlalchemy import text
from database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_reset_token_columns():
    """Userテーブルにパスワードリセット用カラムを追加"""
    
    with engine.connect() as conn:
        try:
            # PostgreSQL用
            if "postgresql" in str(engine.url) or "postgres" in str(engine.url):
                logger.info("PostgreSQL: カラム追加開始")
                
                # reset_tokenカラムを追加（存在しない場合のみ）
                conn.execute(text("""
                    DO $$ 
                    BEGIN 
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='users' AND column_name='reset_token'
                        ) THEN
                            ALTER TABLE users ADD COLUMN reset_token VARCHAR(255);
                            CREATE UNIQUE INDEX idx_users_reset_token ON users(reset_token);
                        END IF;
                    END $$;
                """))
                conn.commit()
                
                # reset_token_expiresカラムを追加（存在しない場合のみ）
                conn.execute(text("""
                    DO $$ 
                    BEGIN 
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='users' AND column_name='reset_token_expires'
                        ) THEN
                            ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP WITH TIME ZONE;
                        END IF;
                    END $$;
                """))
                conn.commit()
                
                logger.info("PostgreSQL: カラム追加完了")
                
            # SQLite用
            else:
                logger.info("SQLite: カラム追加開始")
                
                # SQLiteではカラムの存在確認が異なる
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result]
                
                if 'reset_token' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)"))
                    conn.commit()
                    logger.info("reset_tokenカラムを追加しました")
                    
                if 'reset_token_expires' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires DATETIME"))
                    conn.commit()
                    logger.info("reset_token_expiresカラムを追加しました")
                
                logger.info("SQLite: カラム追加完了")
                
            return True
            
        except Exception as e:
            logger.error(f"カラム追加エラー: {e}")
            return False

if __name__ == "__main__":
    if add_reset_token_columns():
        logger.info("✅ マイグレーション成功")
    else:
        logger.error("❌ マイグレーション失敗")
