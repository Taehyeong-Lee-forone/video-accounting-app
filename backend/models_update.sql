-- データベーススキーマ更新SQL
-- 既存テーブルにユーザーIDを追加

-- 1. Usersテーブル作成
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    storage_quota_mb INTEGER DEFAULT 10000,
    storage_used_mb INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_username ON users(username);

-- 2. User Sessionsテーブル作成
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_token ON user_sessions(session_token);
CREATE INDEX idx_session_user ON user_sessions(user_id);
CREATE INDEX idx_session_expires ON user_sessions(expires_at);

-- 3. Videosテーブルにuser_id追加
ALTER TABLE videos ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS cloud_url VARCHAR(500);  -- クラウドストレージURL
ALTER TABLE videos ADD COLUMN IF NOT EXISTS file_size_mb FLOAT;      -- ファイルサイズ（MB）

-- 既存データ用のデフォルトユーザー作成
INSERT INTO users (email, username, hashed_password, full_name, is_superuser)
VALUES ('admin@example.com', 'admin', '$2b$12$LQKVw0YP5z5X6qT7VQwJXu5J3ZHzNM8dX6J3ZHzNM8dX6', 'Administrator', TRUE)
ON CONFLICT (email) DO NOTHING;

-- 既存ビデオをadminユーザーに割り当て
UPDATE videos SET user_id = (SELECT id FROM users WHERE username = 'admin') WHERE user_id IS NULL;

-- user_idを必須にする（既存データ処理後）
ALTER TABLE videos ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE videos ADD CONSTRAINT fk_video_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 4. Receiptsテーブルにuser_id追加
ALTER TABLE receipts ADD COLUMN IF NOT EXISTS user_id INTEGER;
UPDATE receipts SET user_id = (SELECT user_id FROM videos WHERE videos.id = receipts.video_id) WHERE user_id IS NULL;
ALTER TABLE receipts ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE receipts ADD CONSTRAINT fk_receipt_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 5. Journal Entriesテーブルにuser_id追加
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS user_id INTEGER;
UPDATE journal_entries SET user_id = (SELECT user_id FROM videos WHERE videos.id = journal_entries.video_id) WHERE user_id IS NULL;
ALTER TABLE journal_entries ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE journal_entries ADD CONSTRAINT fk_journal_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 6. インデックス追加（パフォーマンス向上）
CREATE INDEX idx_video_user ON videos(user_id);
CREATE INDEX idx_receipt_user ON receipts(user_id);
CREATE INDEX idx_journal_user ON journal_entries(user_id);