-- Supabase SQL Editor에서 실행할 SQL
-- https://supabase.com/dashboard/project/cphbbpvhfbmwqkcrhhwm/editor

-- 1. 기존 users 테이블 삭제 (있는 경우)
DROP TABLE IF EXISTS users CASCADE;

-- 2. users 테이블 생성
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
);

-- 3. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 4. 초기 관리자 계정 추가
-- 비밀번호: admin123 (bcrypt hash)
INSERT INTO users (email, username, hashed_password, full_name, is_active, is_superuser, storage_quota_mb)
VALUES (
    'admin@example.com',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGfG5Y0YeRm', -- admin123
    'System Administrator',
    true,
    true,
    50000
);

-- 5. 테이블 권한 설정
GRANT ALL ON users TO postgres;
GRANT ALL ON users_id_seq TO postgres;