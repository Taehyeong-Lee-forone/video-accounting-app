#!/usr/bin/env python3
"""
処理中のビデオを強制的に完了状態にする
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Supabase接続URL
DATABASE_URL = "postgresql://postgres.dhbzrmokkyeevuphhkrd:Xogud2960!\"@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"

print("="*50)
print("処理中ビデオの強制完了")
print("="*50)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        print("\n1. データベース接続成功")
        
        # 処理中のビデオを確認
        print("\n2. 処理中のビデオ確認...")
        result = conn.execute(text("""
            SELECT id, filename, status, created_at
            FROM videos
            WHERE status = 'processing'
            ORDER BY created_at DESC
        """))
        
        processing_videos = result.fetchall()
        
        if not processing_videos:
            print("   処理中のビデオはありません")
        else:
            print(f"   {len(processing_videos)}個の処理中ビデオを発見:")
            for video in processing_videos:
                print(f"   - ID: {video[0]}, File: {video[1]}, Status: {video[2]}")
            
            # 強制的にcompletedに変更
            print("\n3. ステータスを'completed'に変更中...")
            conn.execute(text("""
                UPDATE videos 
                SET status = 'done',
                    progress = 100,
                    progress_message = '手動で完了',
                    processing_completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = 'processing'
            """))
            
            print(f"   ✅ {len(processing_videos)}個のビデオを完了状態に変更")
            
            # ダミーのフレームを追加（最低限の動作確認用）
            print("\n4. ダミーフレーム追加中...")
            for video in processing_videos:
                video_id = video[0]
                
                # 既存のフレームがあるか確認
                frame_check = conn.execute(text("""
                    SELECT COUNT(*) FROM frames WHERE video_id = :video_id
                """), {"video_id": video_id})
                frame_count = frame_check.scalar()
                
                if frame_count == 0:
                    # ダミーフレームを1つ追加
                    conn.execute(text("""
                        INSERT INTO frames (video_id, frame_number, timestamp, file_path, is_receipt, created_at)
                        VALUES (:video_id, 1, 0, 'dummy', false, CURRENT_TIMESTAMP)
                    """), {"video_id": video_id})
                    print(f"   - Video {video_id}にダミーフレーム追加")
                else:
                    print(f"   - Video {video_id}には既に{frame_count}個のフレームあり")
        
        # 最終確認
        print("\n5. 最終ステータス確認...")
        result = conn.execute(text("""
            SELECT status, COUNT(*) 
            FROM videos 
            GROUP BY status
            ORDER BY status
        """))
        
        for row in result:
            print(f"   - {row[0]}: {row[1]}個")
    
    print("\n" + "="*50)
    print("✅ 処理完了!")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ エラー発生: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.dispose()