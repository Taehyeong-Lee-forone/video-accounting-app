#!/usr/bin/env python3
"""
Supabaseデータベースにテーブルを作成
"""
import os
import sys
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# Render環境をシミュレート（Supabaseを使用）
os.environ["RENDER"] = "false"  # ローカルでもSupabaseを使用

# DATABASE_URLを明示的に設定
supabase_url = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
os.environ["DATABASE_URL"] = supabase_url

print("="*50)
print("Supabase データベーステーブル作成")
print("="*50)

try:
    from database import engine, Base
    from models import User, Video, Frame, Receipt, JournalEntry, Account, ReceiptHistory
    
    print("\n1. データベース接続確認...")
    print(f"   接続先: Supabase PostgreSQL")
    
    print("\n2. テーブル作成中...")
    # すべてのテーブルを作成
    Base.metadata.create_all(bind=engine)
    print("   ✅ テーブル作成完了")
    
    print("\n3. 作成されたテーブル:")
    for table in Base.metadata.tables.keys():
        print(f"   - {table}")
    
    # 初期管理者作成
    print("\n4. 初期管理者アカウント作成...")
    from database import SessionLocal
    from services.auth_service import get_password_hash
    
    db = SessionLocal()
    try:
        # 既存の管理者確認
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        if not existing_admin:
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
        print(f"\n5. 現在のユーザー数: {user_count}名")
        
    finally:
        db.close()
    
    print("\n✅ データベースセットアップ完了!")
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)