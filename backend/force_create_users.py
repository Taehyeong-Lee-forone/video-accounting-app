#!/usr/bin/env python3
"""
Supabaseに強制的にusersテーブルを作成
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数を読み込み
load_dotenv()

# Supabase接続URL
DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("Supabase Users テーブル強制作成")
print("="*50)

# 新しいエンジンを作成（直接接続）
engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # 既存のusersテーブルを削除（CASCADE）
        print("\n2. 既存のテーブルを削除中...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            print("   ✓ 既存テーブル削除完了")
        except Exception as e:
            print(f"   ⚠ 削除エラー（無視）: {e}")
        
        # usersテーブルを作成
        print("\n3. usersテーブルを作成中...")
        create_table_sql = """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(50) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT true,
            is_superuser BOOLEAN DEFAULT false,
            storage_quota_mb INTEGER DEFAULT 100,
            storage_used_mb FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP
        )
        """
        conn.execute(text(create_table_sql))
        print("   ✅ usersテーブル作成完了")
        
        # インデックス作成
        print("\n4. インデックスを作成中...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
        print("   ✅ インデックス作成完了")
        
        # 初期管理者を追加
        print("\n5. 初期管理者アカウントを作成中...")
        
        # まずbcryptハッシュを生成
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("admin123")
        
        insert_admin = """
        INSERT INTO users (email, username, hashed_password, full_name, is_active, is_superuser, storage_quota_mb)
        VALUES (:email, :username, :hashed_password, :full_name, :is_active, :is_superuser, :storage_quota_mb)
        ON CONFLICT (username) DO NOTHING
        """
        
        conn.execute(text(insert_admin), {
            "email": "admin@example.com",
            "username": "admin",
            "hashed_password": hashed_password,
            "full_name": "System Administrator",
            "is_active": True,
            "is_superuser": True,
            "storage_quota_mb": 50000
        })
        print("   ✅ 管理者アカウント作成完了")
        print("      Username: admin")
        print("      Password: admin123")
        
        # テーブル確認
        print("\n6. テーブル作成確認...")
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()
        print(f"   ✅ usersテーブル内のレコード数: {user_count}")
        
        # ユーザーリスト表示
        result = conn.execute(text("SELECT username, email FROM users"))
        users = result.fetchall()
        if users:
            print("\n7. 登録済みユーザー:")
            for user in users:
                print(f"   - {user[0]} ({user[1]})")
    
    print("\n" + "="*50)
    print("✅ セットアップ完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()