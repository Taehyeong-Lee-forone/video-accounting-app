#!/usr/bin/env python3
"""
既存テーブルにuser_idカラムを追加
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("テーブル構造修正")
print("="*50)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # videosテーブルの構造確認
        print("\n2. videosテーブル構造確認中...")
        check_columns = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'videos'
        ORDER BY ordinal_position;
        """
        result = conn.execute(text(check_columns))
        columns = result.fetchall()
        
        print("   現在のカラム:")
        has_user_id = False
        for col in columns:
            print(f"   - {col[0]}: {col[1]}")
            if col[0] == 'user_id':
                has_user_id = True
        
        # user_idカラムがない場合は追加
        if not has_user_id:
            print("\n3. user_idカラムを追加中...")
            conn.execute(text("ALTER TABLE videos ADD COLUMN IF NOT EXISTS user_id INTEGER"))
            print("   ✅ user_idカラム追加完了")
        else:
            print("\n3. user_idカラムは既に存在します")
        
        # receipts_historyテーブルをreceipt_historiesに修正
        print("\n4. receipt_historyテーブル名修正中...")
        try:
            conn.execute(text("ALTER TABLE receipt_history RENAME TO receipt_histories"))
            print("   ✅ テーブル名修正完了")
        except:
            print("   ℹ️ 既に修正済みまたは存在しません")
        
        # accountsテーブル作成
        print("\n5. accountsテーブル作成中...")
        create_accounts = """
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            category VARCHAR(50),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        conn.execute(text(create_accounts))
        
        # 基本的な勘定科目を追加
        insert_accounts = """
        INSERT INTO accounts (code, name, category) VALUES
            ('1000', '現金', '資産'),
            ('1100', '当座預金', '資産'),
            ('1200', '普通預金', '資産'),
            ('2000', '買掛金', '負債'),
            ('2100', '未払金', '負債'),
            ('3000', '資本金', '資本'),
            ('4000', '売上高', '収益'),
            ('5000', '仕入高', '費用'),
            ('5100', '消耗品費', '費用'),
            ('5200', '交通費', '費用'),
            ('5300', '通信費', '費用'),
            ('5400', '接待交際費', '費用'),
            ('5500', '会議費', '費用'),
            ('5600', '事務用品費', '費用'),
            ('5700', '水道光熱費', '費用'),
            ('5800', '支払手数料', '費用'),
            ('5900', '雑費', '費用'),
            ('6000', '仮払消費税', '資産'),
            ('6100', '仮受消費税', '負債')
        ON CONFLICT (code) DO NOTHING;
        """
        conn.execute(text(insert_accounts))
        print("   ✅ accountsテーブル作成・データ投入完了")
        
        # 最終確認
        print("\n6. 全テーブル確認...")
        check_tables = """
        SELECT table_name, 
               (SELECT COUNT(*) FROM information_schema.columns 
                WHERE columns.table_name = tables.table_name) as column_count
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        result = conn.execute(text(check_tables))
        tables = result.fetchall()
        
        print("   テーブル一覧:")
        for table in tables:
            print(f"   - {table[0]}: {table[1]} columns")
    
    print("\n" + "="*50)
    print("✅ テーブル修正完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()