#!/usr/bin/env python3
"""
ユーザーシステムを追加するマイグレーションスクリプト
既存のデータを保持しながら、ユーザー機能を追加
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging
from passlib.context import CryptContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def migrate_to_user_system():
    """ユーザーシステムを追加"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set in environment")
        return False
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                logger.info("Starting user system migration...")
                
                # 1. Usersテーブル作成
                logger.info("Creating users table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        username VARCHAR(100) UNIQUE NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        full_name VARCHAR(255),
                        is_active BOOLEAN DEFAULT TRUE,
                        is_superuser BOOLEAN DEFAULT FALSE,
                        storage_quota_mb INTEGER DEFAULT 10000,
                        storage_used_mb FLOAT DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE,
                        last_login_at TIMESTAMP WITH TIME ZONE
                    )
                """))
                
                # インデックス作成
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_username ON users(username)"))
                logger.info("✓ Users table created")
                
                # 2. デフォルトadminユーザー作成
                logger.info("Creating default admin user...")
                # パスワード: admin123 (本番環境では変更してください)
                hashed_password = pwd_context.hash("admin123")
                
                conn.execute(text("""
                    INSERT INTO users (email, username, hashed_password, full_name, is_superuser)
                    VALUES (:email, :username, :hashed_password, :full_name, :is_superuser)
                    ON CONFLICT (email) DO NOTHING
                """), {
                    "email": "admin@example.com",
                    "username": "admin",
                    "hashed_password": hashed_password,
                    "full_name": "Administrator",
                    "is_superuser": True
                })
                logger.info("✓ Default admin user created (username: admin, password: admin123)")
                
                # 3. 各テーブルにuser_idカラムを追加
                tables_to_update = [
                    ("videos", "user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"),
                    ("videos", "cloud_url VARCHAR(500)"),
                    ("videos", "file_size_mb FLOAT"),
                    ("receipts", "user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"),
                    ("journal_entries", "user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"),
                ]
                
                for table, column_def in tables_to_update:
                    column_name = column_def.split()[0]
                    try:
                        logger.info(f"Adding {column_name} to {table}...")
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_def}"))
                        logger.info(f"✓ Added {column_name} to {table}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            logger.info(f"✓ Column {column_name} already exists in {table}")
                        else:
                            logger.warning(f"⚠ Warning adding {column_name} to {table}: {e}")
                
                # 4. adminユーザーのIDを取得
                result = conn.execute(text("SELECT id FROM users WHERE username = 'admin'"))
                admin_id = result.scalar()
                
                if admin_id:
                    # 5. 既存データをadminユーザーに割り当て
                    logger.info(f"Assigning existing data to admin user (id={admin_id})...")
                    
                    # Videos
                    conn.execute(text("UPDATE videos SET user_id = :admin_id WHERE user_id IS NULL"), {"admin_id": admin_id})
                    
                    # Receipts (videosのuser_idから取得)
                    conn.execute(text("""
                        UPDATE receipts 
                        SET user_id = (SELECT user_id FROM videos WHERE videos.id = receipts.video_id)
                        WHERE user_id IS NULL
                    """))
                    
                    # Journal Entries (videosのuser_idから取得)
                    conn.execute(text("""
                        UPDATE journal_entries 
                        SET user_id = (SELECT user_id FROM videos WHERE videos.id = journal_entries.video_id)
                        WHERE user_id IS NULL
                    """))
                    
                    logger.info("✓ Existing data assigned to admin user")
                    
                    # 6. ストレージ使用量を計算
                    result = conn.execute(text("""
                        SELECT COALESCE(SUM(file_size_mb), 0) 
                        FROM videos 
                        WHERE user_id = :admin_id
                    """), {"admin_id": admin_id})
                    
                    total_size = result.scalar()
                    conn.execute(text("""
                        UPDATE users 
                        SET storage_used_mb = :total_size 
                        WHERE id = :admin_id
                    """), {"total_size": total_size, "admin_id": admin_id})
                    
                    logger.info(f"✓ Storage usage calculated: {total_size:.2f} MB")
                
                # 7. インデックス追加
                indexes = [
                    ("idx_video_user", "videos", "user_id"),
                    ("idx_receipt_user", "receipts", "user_id"),
                    ("idx_journal_user", "journal_entries", "user_id"),
                ]
                
                for idx_name, table, column in indexes:
                    try:
                        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"))
                        logger.info(f"✓ Index {idx_name} created")
                    except Exception as e:
                        logger.warning(f"⚠ Index {idx_name} may already exist: {e}")
                
                # コミット
                trans.commit()
                logger.info("\n✅ User system migration completed successfully!")
                logger.info("\n📝 Next steps:")
                logger.info("1. Login with: username=admin, password=admin123")
                logger.info("2. Change the admin password immediately")
                logger.info("3. Create new users as needed")
                
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_migration_status():
    """マイグレーション状態を確認"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set in environment")
        return
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # テーブル存在確認
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                )
            """))
            
            if result.scalar():
                logger.info("✅ Users table exists")
                
                # ユーザー数確認
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                logger.info(f"   Total users: {user_count}")
                
                # user_idカラム確認
                for table in ['videos', 'receipts', 'journal_entries']:
                    result = conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns 
                            WHERE table_name = '{table}' 
                            AND column_name = 'user_id'
                        )
                    """))
                    
                    if result.scalar():
                        logger.info(f"✅ {table}.user_id exists")
                    else:
                        logger.warning(f"⚠ {table}.user_id missing")
            else:
                logger.info("⚠ Users table does not exist - migration needed")
                
    except Exception as e:
        logger.error(f"Check failed: {e}")

if __name__ == "__main__":
    print("""
    ====================================
    User System Migration
    ====================================
    
    This script will:
    1. Create users table
    2. Add user_id to all tables
    3. Create default admin user
    4. Assign existing data to admin
    
    """)
    
    if "--check" in sys.argv:
        check_migration_status()
    elif "--apply" in sys.argv:
        if input("Apply user system migration? (yes/no): ").lower() == "yes":
            if migrate_to_user_system():
                print("\n✅ Migration successful!")
            else:
                print("\n❌ Migration failed. Check logs above.")
    else:
        print("Usage:")
        print("  python migrate_add_users.py --check    # Check current status")
        print("  python migrate_add_users.py --apply    # Apply migration")
        print("\nRun with --check first to see current status")