#!/usr/bin/env python3
"""
usersテーブルのみ作成（他のテーブルは既存）
"""
import os
from dotenv import load_dotenv
from sqlalchemy import text

# 環境変数を読み込み
load_dotenv()

# DATABASE_URLを明示的に設定
supabase_url = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
os.environ["DATABASE_URL"] = supabase_url

print("="*50)
print("Users テーブル作成")
print("="*50)

try:
    from database import engine
    
    # SQLで直接usersテーブルを作成
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
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
    );
    """
    
    with engine.begin() as conn:  # begin()を使用してトランザクション管理
        print("1. データベース接続成功")
        
        # テーブル存在確認
        check_table = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'users'
        );
        """
        result = conn.execute(text(check_table))
        exists = result.scalar()
        
        if exists:
            print("2. usersテーブルは既に存在します")
        else:
            print("2. usersテーブルを作成中...")
            conn.execute(text(create_users_table))
            print("   ✅ usersテーブル作成完了")
        
        # 初期管理者作成
        print("\n3. 初期管理者アカウント確認...")
        from database import SessionLocal
        from models import User
        from services.auth_service import get_password_hash
        
        db = SessionLocal()
        try:
            admin = db.query(User).filter(User.username == "admin").first()
            
            if not admin:
                admin_user = User(
                    email="admin@example.com",
                    username="admin",
                    hashed_password=get_password_hash("admin123"),
                    full_name="System Administrator",
                    is_active=True,
                    is_superuser=True,
                    storage_quota_mb=50000
                )
                db.add(admin_user)
                db.commit()
                print("   ✅ 管理者アカウント作成完了")
                print("      Username: admin")
                print("      Password: admin123")
            else:
                print("   ℹ️ 管理者アカウントは既に存在します")
            
            # ユーザー数確認
            user_count = db.query(User).count()
            print(f"\n4. 現在のユーザー数: {user_count}名")
            
            # ユーザーリスト表示
            users = db.query(User).all()
            print("\n5. 登録済みユーザー:")
            for user in users:
                print(f"   - {user.username} ({user.email})")
            
        finally:
            db.close()
    
    print("\n✅ セットアップ完了!")
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()