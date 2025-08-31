#!/usr/bin/env python3
"""
Supabaseに全てのテーブルを作成
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
print("Supabase 全テーブル作成")
print("="*50)

# 新しいエンジンを作成
engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # 既存テーブルの確認
        print("\n2. 既存テーブル確認中...")
        check_tables = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        result = conn.execute(text(check_tables))
        existing_tables = [row[0] for row in result]
        
        if existing_tables:
            print("   既存のテーブル:")
            for table in existing_tables:
                print(f"   - {table}")
        else:
            print("   テーブルが存在しません")
        
        # 3. videosテーブル作成
        print("\n3. videosテーブル作成中...")
        create_videos = """
        CREATE TABLE IF NOT EXISTS videos (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255),
            file_path VARCHAR(500),
            file_size BIGINT,
            duration FLOAT,
            fps FLOAT,
            width INTEGER,
            height INTEGER,
            status VARCHAR(50) DEFAULT 'pending',
            processing_started_at TIMESTAMP,
            processing_completed_at TIMESTAMP,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);
        CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
        """
        conn.execute(text(create_videos))
        print("   ✅ videosテーブル作成完了")
        
        # 4. framesテーブル作成
        print("\n4. framesテーブル作成中...")
        create_frames = """
        CREATE TABLE IF NOT EXISTS frames (
            id SERIAL PRIMARY KEY,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            frame_number INTEGER NOT NULL,
            timestamp FLOAT NOT NULL,
            file_path VARCHAR(500),
            ocr_text TEXT,
            ocr_confidence FLOAT,
            is_receipt BOOLEAN DEFAULT false,
            receipt_confidence FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_frames_video_id ON frames(video_id);
        CREATE INDEX IF NOT EXISTS idx_frames_is_receipt ON frames(is_receipt);
        """
        conn.execute(text(create_frames))
        print("   ✅ framesテーブル作成完了")
        
        # 5. receiptsテーブル作成
        print("\n5. receiptsテーブル作成中...")
        create_receipts = """
        CREATE TABLE IF NOT EXISTS receipts (
            id SERIAL PRIMARY KEY,
            video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
            best_frame_id INTEGER REFERENCES frames(id),
            store_name VARCHAR(255),
            date DATE,
            total_amount DECIMAL(10, 2),
            tax_amount DECIMAL(10, 2),
            receipt_number VARCHAR(100),
            payment_method VARCHAR(50),
            raw_text TEXT,
            confidence_score FLOAT,
            status VARCHAR(50) DEFAULT 'detected',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_receipts_video_id ON receipts(video_id);
        CREATE INDEX IF NOT EXISTS idx_receipts_date ON receipts(date);
        """
        conn.execute(text(create_receipts))
        print("   ✅ receiptsテーブル作成完了")
        
        # 6. journal_entriesテーブル作成
        print("\n6. journal_entriesテーブル作成中...")
        create_journal = """
        CREATE TABLE IF NOT EXISTS journal_entries (
            id SERIAL PRIMARY KEY,
            receipt_id INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            description TEXT,
            debit_account VARCHAR(100),
            debit_amount DECIMAL(10, 2),
            credit_account VARCHAR(100),
            credit_amount DECIMAL(10, 2),
            tax_rate DECIMAL(5, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_journal_receipt_id ON journal_entries(receipt_id);
        CREATE INDEX IF NOT EXISTS idx_journal_date ON journal_entries(date);
        """
        conn.execute(text(create_journal))
        print("   ✅ journal_entriesテーブル作成完了")
        
        # 7. accountsテーブル作成（勘定科目マスター）
        print("\n7. accountsテーブル作成中...")
        create_accounts = """
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            category VARCHAR(50),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 基本的な勘定科目を追加
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
        conn.execute(text(create_accounts))
        print("   ✅ accountsテーブル作成完了")
        
        # 8. receipt_historiesテーブル作成
        print("\n8. receipt_historiesテーブル作成中...")
        create_history = """
        CREATE TABLE IF NOT EXISTS receipt_histories (
            id SERIAL PRIMARY KEY,
            receipt_id INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id),
            action VARCHAR(50) NOT NULL,
            old_data JSONB,
            new_data JSONB,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_history_receipt ON receipt_histories(receipt_id);
        CREATE INDEX IF NOT EXISTS idx_history_user ON receipt_histories(user_id);
        CREATE INDEX IF NOT EXISTS idx_history_changed ON receipt_histories(changed_at);
        """
        conn.execute(text(create_history))
        print("   ✅ receipt_historiesテーブル作成完了")
        
        # 最終確認
        print("\n9. 作成されたテーブル確認中...")
        result = conn.execute(text(check_tables))
        final_tables = [row[0] for row in result]
        
        print("   作成済みテーブル:")
        for table in final_tables:
            # テーブルのレコード数も確認
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.scalar()
            print(f"   - {table}: {count} records")
    
    print("\n" + "="*50)
    print("✅ 全テーブル作成完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()