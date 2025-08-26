-- Supabase (PostgreSQL) スキーマ
-- Video Accounting App Database Schema

-- ENUMタイプの作成
CREATE TYPE video_status AS ENUM ('queued', 'processing', 'done', 'error');
CREATE TYPE journal_status AS ENUM ('unconfirmed', 'confirmed', 'rejected', 'pending');
CREATE TYPE document_type AS ENUM ('領収書', '請求書', 'レシート', '見積書', 'その他', '請求書・領収書');
CREATE TYPE payment_method AS ENUM ('現金', 'クレジット', '電子マネー', '不明');
CREATE TYPE account_type AS ENUM ('debit', 'credit');

-- Videosテーブル
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    gcs_uri VARCHAR(500),
    local_path VARCHAR(500),
    thumbnail_path VARCHAR(500),
    duration_ms INTEGER,
    status video_status DEFAULT 'queued' NOT NULL,
    progress INTEGER DEFAULT 0,
    progress_message VARCHAR(500),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ
);

-- インデックス
CREATE INDEX idx_video_status ON videos(status);
CREATE INDEX idx_video_created ON videos(created_at);

-- Framesテーブル
CREATE TABLE frames (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    time_ms INTEGER NOT NULL,
    sharpness FLOAT,
    brightness FLOAT,
    contrast FLOAT,
    ocr_text TEXT,
    phash VARCHAR(64),
    dhash VARCHAR(64),
    is_best BOOLEAN DEFAULT FALSE,
    is_manual BOOLEAN DEFAULT FALSE,
    ocr_boxes_json TEXT,
    frame_score FLOAT,
    doc_quad_json TEXT,
    sharpness_score FLOAT,
    doc_area_score FLOAT,
    perspective_score FLOAT,
    exposure_score FLOAT,
    stability_score FLOAT,
    glare_penalty FLOAT,
    textness_score FLOAT,
    total_quality_score FLOAT,
    motion_score FLOAT,
    frame_path VARCHAR(500)
);

-- インデックス
CREATE INDEX idx_frame_video_time ON frames(video_id, time_ms);
CREATE INDEX idx_frame_best ON frames(video_id, is_best);
CREATE INDEX idx_frame_phash ON frames(phash);

-- Receiptsテーブル
CREATE TABLE receipts (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    best_frame_id INTEGER REFERENCES frames(id) ON DELETE SET NULL,
    vendor VARCHAR(255),
    vendor_norm VARCHAR(255),
    total FLOAT,
    subtotal FLOAT,
    tax FLOAT,
    issue_date TIMESTAMPTZ,
    document_type document_type DEFAULT '領収書',
    payment_method payment_method DEFAULT '不明',
    memo TEXT,
    status VARCHAR(50) DEFAULT 'unconfirmed',
    ocr_raw_text TEXT,
    document_number VARCHAR(100),
    phone_number VARCHAR(50),
    address TEXT,
    is_manual BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ
);

-- インデックス
CREATE INDEX idx_receipt_video ON receipts(video_id);
CREATE INDEX idx_receipt_vendor ON receipts(vendor);
CREATE INDEX idx_receipt_date ON receipts(issue_date);

-- Journal Entriesテーブル
CREATE TABLE journal_entries (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    receipt_id INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
    transaction_date DATE NOT NULL,
    description TEXT,
    status journal_status DEFAULT 'unconfirmed',
    confirmed_by VARCHAR(100),
    confirmed_at TIMESTAMPTZ,
    memo TEXT,
    debit_total DECIMAL(12, 2),
    credit_total DECIMAL(12, 2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ
);

-- インデックス
CREATE INDEX idx_journal_video ON journal_entries(video_id);
CREATE INDEX idx_journal_receipt ON journal_entries(receipt_id);
CREATE INDEX idx_journal_date ON journal_entries(transaction_date);
CREATE INDEX idx_journal_status ON journal_entries(status);

-- Journal Entry Linesテーブル
CREATE TABLE journal_entry_lines (
    id SERIAL PRIMARY KEY,
    journal_entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_code VARCHAR(50),
    account_name VARCHAR(255) NOT NULL,
    account_type account_type NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    tax_rate DECIMAL(5, 2),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_journal_line_entry ON journal_entry_lines(journal_entry_id);
CREATE INDEX idx_journal_line_account ON journal_entry_lines(account_code);

-- Receipt Historyテーブル
CREATE TABLE receipt_history (
    id SERIAL PRIMARY KEY,
    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(100),
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_history_receipt ON receipt_history(receipt_id);
CREATE INDEX idx_history_changed ON receipt_history(changed_at);

-- Updated_at トリガー関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- トリガー作成
CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_receipts_updated_at BEFORE UPDATE ON receipts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_journal_entries_updated_at BEFORE UPDATE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) を有効化（オプション）
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE frames ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entry_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipt_history ENABLE ROW LEVEL SECURITY;