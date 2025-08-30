#!/usr/bin/env python3
"""
データベースのenum型をstring型に変換するスクリプト
PostgreSQLのenum型とSQLAlchemyのString型の不一致を解決
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def fix_database_enums():
    """enum型をstring型に変換し、値を正規化"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set in environment")
        return False
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # トランザクション開始
            trans = conn.begin()
            
            try:
                logger.info("Starting database enum migration...")
                
                # 1. enum型をvarchar型に変換
                migrations = [
                    # Videos table
                    "ALTER TABLE videos ALTER COLUMN status TYPE varchar(20) USING status::text",
                    
                    # Receipts table
                    "ALTER TABLE receipts ALTER COLUMN status TYPE varchar(20) USING status::text",
                    "ALTER TABLE receipts ALTER COLUMN document_type TYPE varchar(50) USING document_type::text",
                    "ALTER TABLE receipts ALTER COLUMN payment_method TYPE varchar(20) USING payment_method::text",
                    
                    # Journal entries table  
                    "ALTER TABLE journal_entries ALTER COLUMN status TYPE varchar(20) USING status::text",
                    
                    # Vendors table
                    "ALTER TABLE vendors ALTER COLUMN default_payment_method TYPE varchar(20) USING default_payment_method::text",
                ]
                
                for migration in migrations:
                    try:
                        logger.info(f"Executing: {migration[:50]}...")
                        conn.execute(text(migration))
                        logger.info("✓ Success")
                    except Exception as e:
                        if "does not exist" in str(e):
                            logger.info("✓ Column already migrated or doesn't exist")
                        else:
                            logger.warning(f"⚠ Warning: {e}")
                
                # 2. 値を小文字に正規化
                normalizations = [
                    "UPDATE videos SET status = LOWER(status) WHERE status IS NOT NULL",
                    "UPDATE receipts SET status = LOWER(status) WHERE status IS NOT NULL",
                    "UPDATE journal_entries SET status = LOWER(status) WHERE status IS NOT NULL",
                ]
                
                for normalization in normalizations:
                    try:
                        logger.info(f"Normalizing: {normalization[:50]}...")
                        result = conn.execute(text(normalization))
                        logger.info(f"✓ Updated {result.rowcount} rows")
                    except Exception as e:
                        logger.warning(f"⚠ Warning: {e}")
                
                # 3. enum型を削除（依存関係があるため注意）
                drop_types = [
                    "DROP TYPE IF EXISTS video_status CASCADE",
                    "DROP TYPE IF EXISTS journal_status CASCADE", 
                    "DROP TYPE IF EXISTS document_type CASCADE",
                    "DROP TYPE IF EXISTS payment_method CASCADE",
                ]
                
                for drop_type in drop_types:
                    try:
                        logger.info(f"Dropping: {drop_type}")
                        conn.execute(text(drop_type))
                        logger.info("✓ Success")
                    except Exception as e:
                        logger.warning(f"⚠ Type may not exist: {e}")
                
                # コミット
                trans.commit()
                logger.info("\n✅ Database migration completed successfully!")
                
                # 4. 現在の状態を確認
                logger.info("\n📊 Verifying current state...")
                
                # Videos table status値の確認
                result = conn.execute(text("SELECT DISTINCT status FROM videos"))
                statuses = [row[0] for row in result]
                logger.info(f"Video statuses in DB: {statuses}")
                
                # Receipts table status値の確認
                result = conn.execute(text("SELECT DISTINCT status FROM receipts"))
                statuses = [row[0] for row in result]
                logger.info(f"Receipt statuses in DB: {statuses}")
                
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_current_state():
    """現在のデータベース状態を確認"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set in environment")
        return
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # カラムの型を確認
            query = """
            SELECT 
                table_name,
                column_name,
                data_type,
                udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND column_name IN ('status', 'document_type', 'payment_method')
            ORDER BY table_name, column_name
            """
            
            result = conn.execute(text(query))
            
            logger.info("\n📋 Current column types:")
            logger.info("-" * 60)
            for row in result:
                logger.info(f"{row[0]}.{row[1]}: {row[2]} ({row[3]})")
            
            # enum型の存在確認
            query = """
            SELECT typname
            FROM pg_type
            WHERE typtype = 'e'
            AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            """
            
            result = conn.execute(text(query))
            enums = [row[0] for row in result]
            
            if enums:
                logger.info(f"\n⚠️  Existing enum types: {enums}")
            else:
                logger.info("\n✅ No enum types found (good!)")
                
    except Exception as e:
        logger.error(f"Check failed: {e}")

if __name__ == "__main__":
    print("""
    ====================================
    PostgreSQL Enum to String Migration
    ====================================
    
    This script will:
    1. Convert enum columns to varchar
    2. Normalize values to lowercase
    3. Drop enum types
    
    """)
    
    if "--check" in sys.argv:
        check_current_state()
    elif "--apply" in sys.argv:
        if input("Are you sure you want to apply migration? (yes/no): ").lower() == "yes":
            if fix_database_enums():
                print("\n✅ Migration successful!")
            else:
                print("\n❌ Migration failed. Check logs above.")
    else:
        print("Usage:")
        print("  python fix_database_enums.py --check    # Check current state")
        print("  python fix_database_enums.py --apply    # Apply migration")
        print("\nRun with --check first to see current state")