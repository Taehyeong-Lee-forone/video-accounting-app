#!/usr/bin/env python3
"""
SQLite에서 Supabase PostgreSQL로 데이터 마이그레이션
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLite 데이터베이스
SQLITE_URL = "sqlite:///./video_accounting.db"

# Supabase PostgreSQL
POSTGRES_URL = "postgresql://postgres:ZgqvGBD34FBaVXb8@db.cphbbpvhfbmwqkcrhhwm.supabase.co:5432/postgres"

def migrate_data():
    """SQLite에서 PostgreSQL로 데이터 마이그레이션"""
    
    # SQLite 연결
    sqlite_engine = create_engine(SQLITE_URL)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()
    
    # PostgreSQL 연결
    postgres_engine = create_engine(POSTGRES_URL)
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()
    
    try:
        # 모델 임포트
        from models import User, Video, Receipt, JournalEntry, Frame
        from database import Base
        
        logger.info("=== Supabase PostgreSQL 마이그레이션 시작 ===")
        
        # PostgreSQL 테이블 생성
        logger.info("PostgreSQL 테이블 생성 중...")
        Base.metadata.create_all(bind=postgres_engine)
        
        # 1. Users 마이그레이션
        logger.info("\n1. Users 마이그레이션...")
        users = sqlite_session.query(User).all()
        for user in users:
            existing = postgres_session.query(User).filter(User.username == user.username).first()
            if not existing:
                new_user = User(
                    id=user.id,
                    email=user.email,
                    username=user.username,
                    hashed_password=user.hashed_password,
                    full_name=user.full_name,
                    is_active=user.is_active,
                    is_superuser=user.is_superuser,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )
                postgres_session.add(new_user)
        postgres_session.commit()
        logger.info(f"✅ {len(users)} users 마이그레이션 완료")
        
        # 2. Videos 마이그레이션
        logger.info("\n2. Videos 마이그레이션...")
        videos = sqlite_session.query(Video).all()
        video_mapping = {}  # 이전 ID -> 새 ID 매핑
        
        for video in videos:
            new_video = Video(
                filename=video.filename,
                local_path=video.local_path,
                cloud_url=video.cloud_url,
                gcs_uri=video.gcs_uri,
                thumbnail_path=video.thumbnail_path,
                status=video.status or 'completed',
                progress=video.progress or 100,
                user_id=video.user_id,
                created_at=video.created_at,
                updated_at=video.updated_at
            )
            postgres_session.add(new_video)
            postgres_session.flush()  # ID 생성
            video_mapping[video.id] = new_video.id
        
        postgres_session.commit()
        logger.info(f"✅ {len(videos)} videos 마이그레이션 완료")
        
        # 3. Receipts 마이그레이션
        logger.info("\n3. Receipts 마이그레이션...")
        receipts = sqlite_session.query(Receipt).all()
        receipt_mapping = {}
        
        for receipt in receipts:
            if receipt.video_id in video_mapping:
                new_receipt = Receipt(
                    video_id=video_mapping[receipt.video_id],
                    frame_number=receipt.frame_number,
                    time_ms=receipt.time_ms,
                    vendor=receipt.vendor,
                    total_amount=receipt.total_amount,
                    tax_amount=receipt.tax_amount,
                    issue_date=receipt.issue_date,
                    items=receipt.items,
                    raw_text=receipt.raw_text,
                    confidence_score=receipt.confidence_score,
                    is_manual=receipt.is_manual,
                    created_at=receipt.created_at,
                    updated_at=receipt.updated_at
                )
                postgres_session.add(new_receipt)
                postgres_session.flush()
                receipt_mapping[receipt.id] = new_receipt.id
        
        postgres_session.commit()
        logger.info(f"✅ {len(receipts)} receipts 마이그레이션 완료")
        
        # 4. Journal Entries 마이그레이션
        logger.info("\n4. Journal Entries 마이그레이션...")
        journals = sqlite_session.query(JournalEntry).all()
        
        for journal in journals:
            if journal.video_id in video_mapping:
                new_journal = JournalEntry(
                    video_id=video_mapping[journal.video_id],
                    receipt_id=receipt_mapping.get(journal.receipt_id),
                    date=journal.date,
                    description=journal.description,
                    debit_account=journal.debit_account,
                    credit_account=journal.credit_account,
                    debit_amount=journal.debit_amount,
                    credit_amount=journal.credit_amount,
                    tax_amount=journal.tax_amount,
                    created_at=journal.created_at,
                    updated_at=journal.updated_at
                )
                postgres_session.add(new_journal)
        
        postgres_session.commit()
        logger.info(f"✅ {len(journals)} journal entries 마이그레이션 완료")
        
        logger.info("\n=== 마이그레이션 완료 ===")
        logger.info(f"총 {len(videos)} 개의 영상과 관련 데이터를 Supabase로 마이그레이션했습니다.")
        
    except Exception as e:
        logger.error(f"마이그레이션 실패: {e}")
        postgres_session.rollback()
        raise
    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    migrate_data()