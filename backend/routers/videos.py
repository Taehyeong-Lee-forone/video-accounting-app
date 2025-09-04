from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
import os
import shutil
from pathlib import Path
import logging
import cv2
import asyncio

from database import get_db
from models import Video, Frame, Receipt, JournalEntry, ReceiptHistory, User
from schemas import VideoResponse, VideoDetailResponse, VideoAnalyzeRequest, FrameResponse, ReceiptUpdate
from services.video_intelligence import VideoAnalyzer
from services.journal_generator import JournalGenerator
from services.storage import StorageService
from routers.auth import get_optional_current_user
from celery_app import analyze_video_task
from video_processing import select_receipt_frames

logger = logging.getLogger(__name__)

router = APIRouter()

# Supabase Storage サービス初期化
try:
    storage_service = StorageService()
    use_cloud_storage = True
    logger.info("Cloud storage (Supabase) initialized successfully")
except Exception as e:
    logger.warning(f"Cloud storage initialization failed: {e}. Using local storage.")
    storage_service = None
    use_cloud_storage = False

@router.post("/test")
async def test_upload():
    """アップロードテスト用エンドポイント"""
    try:
        # テスト用のディレクトリ作成
        base_dir = Path("/tmp") if os.getenv("RENDER") == "true" else Path("uploads")
        test_dir = base_dir / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # テストファイル作成
        test_file = test_dir / "test.txt"
        test_file.write_text("Test upload successful")
        
        return {
            "status": "success",
            "render_env": os.getenv("RENDER", "false"),
            "base_dir": str(base_dir),
            "test_file": str(test_file),
            "exists": test_file.exists()
        }
    except Exception as e:
        logger.error(f"テストエラー: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/{video_id}/force-complete")
async def force_complete_video(video_id: int, db: Session = Depends(get_db)):
    """処理中のビデオを強制完了させる"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    if video.status == "processing":
        video.status = "done"
        video.progress = 100
        video.progress_message = "強制完了"
        db.commit()
        return {"message": f"Video {video_id} を強制完了しました", "receipts_count": len(video.receipts)}
    else:
        return {"message": f"Video {video_id} は既に {video.status} 状態です"}

@router.get("/test-ocr")
async def test_ocr():
    """OCR設定テスト用エンドポイント"""
    import os
    result = {
        "google_credentials_json": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")),
        "google_credentials_file": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
        "gemini_api_key": bool(os.getenv("GEMINI_API_KEY")),
        "render_env": os.getenv("RENDER", "false")
    }
    
    # Vision APIのテスト
    try:
        from services.vision_ocr import VisionOCRService
        ocr_service = VisionOCRService()
        result["vision_api_initialized"] = bool(ocr_service.client)
    except Exception as e:
        result["vision_api_error"] = str(e)
        result["vision_api_initialized"] = False
    
    return result

@router.post("/", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """動画アップロード"""
    try:
        logger.info(f"=== アップロード開始 ===")
        logger.info(f"ファイル名: {file.filename}")
        logger.info(f"Content-Type: {file.content_type}")
        logger.info(f"Render環境: {os.getenv('RENDER', 'false')}")
        
        # ファイル検証
        if not file.filename:
            raise HTTPException(400, "ファイル名が空です")
            
        if not file.filename.endswith(('.mp4', '.mov', '.avi', '.webm', '.mkv')):
            logger.error(f"サポートされていないファイル形式: {file.filename}")
            raise HTTPException(400, "サポートされていないファイル形式です")
        
        # ファイル保存 - Render環境では/tmpを使用
        base_dir = Path("/tmp") if os.getenv("RENDER") == "true" else Path("uploads")
        logger.info(f"ベースディレクトリ: {base_dir}")
        
        upload_dir = base_dir / "videos"
        logger.info(f"アップロードディレクトリ: {upload_dir}")
        
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"ディレクトリ作成成功: {upload_dir.exists()}")
        except Exception as e:
            logger.error(f"ディレクトリ作成失敗: {e}")
            raise HTTPException(500, f"ディレクトリ作成失敗: {str(e)}")
        
        # ユニークなファイル名を生成
        import time
        timestamp = str(int(time.time() * 1000))
        file_extension = Path(file.filename).suffix or ".mp4"
        unique_filename = f"{timestamp}{file_extension}"
        file_path = upload_dir / unique_filename
        logger.info(f"保存パス: {file_path}")
        
        try:
            # ファイルを一度読み込んでサイズチェックと保存を同時に行う
            file_content = await file.read()
            file_size = len(file_content)
            
            logger.info(f"ファイルサイズ: {file_size / 1024 / 1024:.2f}MB")
            
            if file_size == 0:
                raise HTTPException(400, "ファイルが空です")
            
            if file_size > 100 * 1024 * 1024:  # 100MB制限
                logger.error(f"ファイルサイズが大きすぎます: {file_size / 1024 / 1024:.2f}MB")
                raise HTTPException(400, "ファイルサイズが大きすぎます（最大100MB）")
            
            # ファイル内容を保存
            # ローカル保存（一時的）
            with file_path.open("wb") as buffer:
                buffer.write(file_content)
            
            logger.info(f"ファイル保存成功: {file_path.exists()}")
            
            # Supabase Storageにアップロード
            cloud_url = None
            if use_cloud_storage and storage_service:
                try:
                    # ファイルパス生成（user_idは0で仮設定、後でユーザー認証追加時に修正）
                    cloud_path = storage_service.generate_file_path(0, unique_filename, "video")
                    
                    # アップロード実行
                    loop = asyncio.get_event_loop()
                    success, result = await loop.run_in_executor(
                        None,
                        storage_service.upload_file_sync,
                        file_content,
                        cloud_path,
                        "video/mp4"
                    )
                    
                    if success:
                        cloud_url = result
                        logger.info(f"Cloud storage upload successful: {cloud_url}")
                    else:
                        logger.warning(f"Cloud storage upload failed: {result}")
                except Exception as e:
                    logger.error(f"Cloud storage upload error: {e}")
                    # クラウドアップロード失敗してもローカルは成功しているので続行
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ファイル保存エラー: {e}", exc_info=True)
            raise HTTPException(500, f"ファイル保存失敗: {str(e)}")
        
        # サムネイル生成
        thumbnail_dir = base_dir / "thumbnails"
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_filename = f"{file_path.stem}_thumb.jpg"
        thumbnail_path = thumbnail_dir / thumbnail_filename
        
        try:
            cap = cv2.VideoCapture(str(file_path))
            cap.set(cv2.CAP_PROP_POS_FRAMES, 10)  # 10番目のフレーム（より安定的）
            ret, frame = cap.read()
            if not ret:  # 10番目のフレームがない場合は最初のフレーム
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            
            if ret:
                # リサイズ（幅320pxを維持、比率を維持）
                height, width = frame.shape[:2]
                new_width = 320
                new_height = int(height * (new_width / width))
                resized = cv2.resize(frame, (new_width, new_height))
                cv2.imwrite(str(thumbnail_path), resized)
                logger.info(f"Thumbnail created: {thumbnail_path}")
                
                # Supabase Storageにサムネイルをアップロード
                if use_cloud_storage and storage_service:
                    try:
                        with open(thumbnail_path, 'rb') as f:
                            thumbnail_content = f.read()
                        
                        # クラウドパス生成 (一時的なファイル名を使用)
                        cloud_thumbnail_path = storage_service.generate_file_path(
                            user_id=current_user.id if current_user else 1,
                            filename=f"thumbnail_{timestamp}.jpg",
                            file_type="thumbnail"
                        )
                        
                        success, thumbnail_cloud_url = storage_service.upload_file_sync(
                            file_content=thumbnail_content,
                            file_path=cloud_thumbnail_path,
                            content_type="image/jpeg"
                        )
                        
                        if success:
                            logger.info(f"Thumbnail uploaded to cloud: {thumbnail_cloud_url}")
                            # DBにクラウドURLを保存
                            thumbnail_path = thumbnail_cloud_url
                    except Exception as e:
                        logger.warning(f"Failed to upload thumbnail to cloud: {e}")
            cap.release()
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")
            thumbnail_path = None
        
        # DB登録 - 元のファイル名を保持
        # クラウドURLがあれば優先、なければローカルパス
        if cloud_url:
            db_video_path = cloud_url
            logger.info(f"Using cloud URL for video: {cloud_url}")
        elif os.getenv("RENDER") == "true":
            # /tmp/videos/xxx.mp4 -> uploads/videos/xxx.mp4
            db_video_path = str(file_path).replace("/tmp/", "uploads/")
            db_thumbnail_path = str(thumbnail_path).replace("/tmp/", "uploads/") if thumbnail_path else None
        else:
            db_video_path = str(file_path)
            db_thumbnail_path = str(thumbnail_path) if thumbnail_path else None
            
        video = Video(
            filename=file.filename,  # 元のファイル名を保持
            local_path=db_video_path,  # DBにはクラウドURLまたはローカルパスを保存
            gcs_uri=cloud_url,  # クラウドURLを別途保存
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,  # 文字列に変換して保存
            status="processing",  # 自動的に処理開始
            progress=10,  # 初期進捗を10に設定
            user_id=current_user.id if current_user else None  # ログインしている場合のみユーザーIDを設定
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # サムネイルをクラウドにアップロード（video.idが利用可能になった後）
        if thumbnail_path and use_cloud_storage and storage_service:
            try:
                with open(thumbnail_path, 'rb') as f:
                    thumbnail_content = f.read()
                
                # クラウドパス生成
                cloud_thumbnail_path = storage_service.generate_file_path(
                    user_id=current_user.id if current_user else 1,
                    filename=f"thumbnail_{video.id}.jpg",
                    file_type="thumbnail"
                )
                
                success, thumbnail_cloud_url = storage_service.upload_file_sync(
                    file_content=thumbnail_content,
                    file_path=cloud_thumbnail_path,
                    content_type="image/jpeg"
                )
                
                if success:
                    logger.info(f"Thumbnail uploaded to cloud: {thumbnail_cloud_url}")
                    # DBのサムネイルパスを更新
                    video.thumbnail_path = thumbnail_cloud_url
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to upload thumbnail to cloud: {e}")
        
        # VideoResponseに必要な追加フィールドを設定
        video.receipts_count = 0
        video.auto_receipts_count = 0
        video.manual_receipts_count = 0
        
        logger.info(f"ビデオDB登録成功: ID={video.id}")
        
        # 実際のOCR処理を開始
        try:
            # バックグラウンドで処理を開始（新しいセッションを使用）
            background_tasks.add_task(
                process_video_ocr_wrapper,
                video.id
            )
            logger.info(f"OCR処理開始: ID={video.id}")
            
            # ステータスを処理中に更新
            video.status = "processing"
            video.progress = 10
            db.commit()
            
        except Exception as e:
            logger.error(f"OCR処理開始エラー: {e}")
            # エラーでも動画は保存されているので続行
            video.status = "error"
            video.progress_message = str(e)[:500]  # エラーメッセージを制限
            video.error_message = str(e)[:500]
            try:
                db.commit()
            except:
                db.rollback()
        
        return video
        
    except HTTPException:
        raise  # HTTPExceptionはそのまま再送出
    except Exception as e:
        logger.error(f"動画アップロードエラー: {e}", exc_info=True)
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"詳細エラー: {error_detail}")
        raise HTTPException(500, f"アップロードに失敗しました: {str(e)}")

@router.post("/{video_id}/analyze")
async def analyze_video(
    video_id: int,
    request: VideoAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """動画分析開始"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    if video.status == "processing":
        raise HTTPException(400, "既に分析中です")
    
    # ステータス更新
    video.status = "processing"
    db.commit()
    
    # バックグラウンドタスク開始
    background_tasks.add_task(
        run_video_analysis,
        video_id,
        request.frames_per_second,
        db
    )
    
    return {"message": "分析を開始しました", "video_id": video_id}

async def run_video_analysis(video_id: int, fps: int, db: Session):
    """動画分析の実行"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        analyzer = VideoAnalyzer()
        
        # 進行状況更新関数
        def update_progress(progress: int, message: str):
            video.progress = progress
            video.progress_message = message
            db.commit()
            db.refresh(video)
            logger.info(f"Video {video_id}: {progress}% - {message}")
        
        update_progress(10, "高品質フレーム選択中...")
        
        # 新しい高品質フレーム選択システムを使用
        logger.info("Using new high-quality frame selection system")
        
        # ビデオ時間から目標フレーム数を計算
        import cv2
        cap = cv2.VideoCapture(video.local_path)
        fps_video = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / fps_video if fps_video > 0 else 0
        cap.release()
        
        # 目標レシート数を計算（約2.5秒ごとに1枚、最小7枚、最大15枚）
        target_min = max(7, int(duration_seconds / 3.0))
        target_max = min(15, max(target_min + 3, int(duration_seconds / 2.0)))
        logger.info(f"Video duration: {duration_seconds:.1f}s, target frames: {target_min}-{target_max}")
        
        # 新しいシステムで高品質フレームを選択（OCR込み）
        try:
            selected_frames_new = select_receipt_frames(
                video_path=video.local_path,
                target_min=target_min,
                target_max=target_max
            )
            logger.info(f"Selected {len(selected_frames_new)} high-quality frames")
        except Exception as e:
            logger.error(f"New frame selection failed: {e}, falling back to basic extraction")
            # フォールバック: 基本的なフレーム抽出
            frames_data = analyzer.extract_frames(video.local_path, fps)
            selected_frames_new = []
        
        update_progress(50, "フレームデータ保存中...")
        
        # 新しいシステムを使用している場合は、古い処理をスキップ
        if selected_frames_new:
            update_progress(70, "レシートデータ処理中...")
            receipts_found = 0
            
            # 新しいシステムの結果をデータベースに保存
            for idx, selected_frame in enumerate(selected_frames_new):
                # Frameオブジェクトを作成
                frame_obj = Frame(
                    video_id=video.id,
                    time_ms=int(selected_frame.time_s * 1000),
                    frame_path=selected_frame.crop_path,
                    ocr_text=selected_frame.ocr_text,
                    frame_score=selected_frame.score,
                    is_best=True
                )
                db.add(frame_obj)
                db.flush()
                
                # レシートデータがある場合は保存
                if selected_frame.metadata and selected_frame.metadata.get('receipt_info'):
                    receipt_info = selected_frame.metadata['receipt_info']
                    
                    # 有効なレシートデータか確認
                    if receipt_info and receipt_info.get('vendor'):
                        from datetime import datetime
                        
                        # 日付処理
                        issue_date = receipt_info.get('date')
                        if issue_date and isinstance(issue_date, str):
                            try:
                                issue_date = datetime.strptime(issue_date, '%Y-%m-%d')
                            except:
                                issue_date = datetime.now()
                        elif not issue_date:
                            issue_date = datetime.now()
                        
                        # レシートを保存
                        total_amount = receipt_info.get('total', 0) or 0
                        receipt = Receipt(
                            video_id=video.id,
                            best_frame_id=frame_obj.id,
                            vendor=receipt_info.get('vendor', 'Unknown'),
                            document_type='レシート',
                            issue_date=issue_date,
                            currency=receipt_info.get('currency', 'JPY'),
                            total=total_amount,
                            subtotal=receipt_info.get('subtotal', total_amount * 0.9),
                            tax=receipt_info.get('tax', total_amount * 0.1),
                            tax_rate=0.10,
                            payment_method='現金',
                            is_manual=False
                        )
                        db.add(receipt)
                        receipts_found += 1
                        logger.info(f"Saved receipt {receipts_found}: {receipt_info.get('vendor')} - {receipt_info.get('total')}")
                
                update_progress(70 + (20 * idx // len(selected_frames_new)), f"レシート {idx+1}/{len(selected_frames_new)} 処理中...")
            
            db.commit()
            logger.info(f"Saved {receipts_found} receipts from new system")
            
            # 仕訳データ生成
            update_progress(90, "仕訳データ生成中...")
            generator = JournalGenerator(db)
            receipts = db.query(Receipt).filter(Receipt.video_id == video.id).all()
            
            for receipt in receipts:
                journal_entries = generator.generate_journal_entries(receipt)
                for entry_data in journal_entries:
                    journal_entry = JournalEntry(
                        receipt_id=entry_data.receipt_id,
                        video_id=entry_data.video_id,
                        time_ms=int(receipt.best_frame.time_ms) if receipt.best_frame and receipt.best_frame.time_ms is not None else 0,
                        debit_account=entry_data.debit_account,
                        credit_account=entry_data.credit_account,
                        debit_amount=entry_data.debit_amount,
                        credit_amount=entry_data.credit_amount,
                        tax_account=entry_data.tax_account,
                        tax_amount=entry_data.tax_amount,
                        memo=entry_data.memo,
                        status='unconfirmed'
                    )
                    db.add(journal_entry)
            
            db.commit()
            logger.info(f"Generated journal entries for {len(receipts)} receipts")
            
            # 新システムで完了
            update_progress(100, "分析完了")
            video.status = "done"
            video.progress = 100
            video.progress_message = "分析完了"
            db.commit()
            logger.info(f"Video {video_id} analysis complete with new system")
            return  # 新システム使用時はここで終了
            
        else:
            # フォールバック: 古いシステムを使用
            logger.warning("Using fallback frame selection system")
            
            # 改善されたフレーム分散選択 - 全体均等分割
            def distribute_frames_intelligently(frames_data, target_count):
                """ビデオ全体を均等にカバーするインテリジェントフレーム選択"""
                if not frames_data:
                    return []
                
                # スマートフレーム抽出器を使用した場合、すでに最適化済み
                # すべてのフレームをそのまま使用
                if len(frames_data) <= 30:
                    logger.info(f"Using all {len(frames_data)} smart-extracted frames without filtering")
                    return frames_data
                
                # 時間順にソート
                frames_sorted = sorted(frames_data, key=lambda x: x['time_ms'])
                min_time = frames_sorted[0]['time_ms']
                max_time = frames_sorted[-1]['time_ms']
                duration = max_time - min_time
                
                selected_frames = []
                used_times = set()
                
                # 全区間を均等分割（最初から最後まで）
                if duration > 0 and target_count > 0:
                    # 均等間隔を計算
                    interval = duration / target_count
                    
                    for i in range(target_count):
                        # 各区間の中心時間
                        target_time = min_time + (i * interval) + (interval / 2)
                        
                        # ターゲット時間付近のフレームを探す（±interval/2の範囲）
                        nearby_frames = [
                            f for f in frames_sorted 
                            if abs(f['time_ms'] - target_time) <= interval/2
                            and f['time_ms'] not in used_times
                        ]
                        
                        if not nearby_frames:
                            # 範囲を広げて再検索
                            nearby_frames = [
                                f for f in frames_sorted 
                                if abs(f['time_ms'] - target_time) <= interval
                                and f['time_ms'] not in used_times
                            ]
                        
                        if not nearby_frames:
                            # それでもない場合は全体から最も近いフレーム
                            available_frames = [f for f in frames_sorted if f['time_ms'] not in used_times]
                            if available_frames:
                                nearby_frames = [min(available_frames, key=lambda x: abs(x['time_ms'] - target_time))]
                        
                        if nearby_frames:
                            # ターゲット時間に最も近く品質の良いフレームを選択
                            best_frame = min(nearby_frames, 
                                           key=lambda x: (abs(x['time_ms'] - target_time) / 1000, -x.get('quality_score', 0)))
                            selected_frames.append(best_frame)
                            used_times.add(best_frame['time_ms'])
                            logger.info(f"Segment {i+1}/{target_count} (target: {target_time:.0f}ms): selected frame at {best_frame['time_ms']}ms (score: {best_frame.get('quality_score', 0):.3f})")
                        else:
                            logger.warning(f"Segment {i+1}/{target_count}: No frame available for target {target_time:.0f}ms")
                
                # 最小フレーム数を保証
                if len(selected_frames) < target_count:
                    # まだ選択されていない高品質フレームを追加
                    remaining = [f for f in frames_sorted if f['time_ms'] not in used_times]
                    remaining.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
                    
                    for frame in remaining[:target_count - len(selected_frames)]:
                        selected_frames.append(frame)
                        logger.info(f"Additional high-quality frame at {frame['time_ms']}ms (score: {frame.get('quality_score', 0):.3f})")
                
                # 時間順にソートして返す
                selected_frames.sort(key=lambda x: x['time_ms'])
                return selected_frames
            
            # インテリジェントフレーム選択 - 品質優先モード
            # 1. 品質スコアで上位フレームを選択
            frames_data.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            
            # 2. 高品質フレームのみ選択（閾値: 0.3以上）
            high_quality_frames = [f for f in frames_data if f.get('quality_score', 0) >= 0.3]
            
            if len(high_quality_frames) < 5:  # 最低5枚は必要
                logger.warning(f"Only {len(high_quality_frames)} high quality frames found, using top {min(10, len(frames_data))} frames")
                high_quality_frames = frames_data[:min(10, len(frames_data))]
            
            # 3. 時間的に分散させる（同じシーンの重複を避ける）
            frames_data = []
            used_time_ranges = []  # (start_ms, end_ms) のタプルリスト
            
            for frame in high_quality_frames[:target_max * 2]:  # 候補を多めに取る
                frame_time = frame['time_ms']
                
                # 既存のフレームから2秒以上離れているか確認
                is_far_enough = True
                for start, end in used_time_ranges:
                    if start - 2000 <= frame_time <= end + 2000:  # 2秒以内は近すぎる
                        is_far_enough = False
                        break
                
                if is_far_enough:
                    frames_data.append(frame)
                    used_time_ranges.append((frame_time - 500, frame_time + 500))  # ±0.5秒をマーク
                    
                    if len(frames_data) >= target_max:
                        break
            
            # 4. 最低限必要な枚数を確保
            if len(frames_data) < min(5, len(high_quality_frames)):
                # 品質優先で追加
                for frame in high_quality_frames:
                    if frame not in frames_data:
                        frames_data.append(frame)
                        if len(frames_data) >= min(10, len(high_quality_frames)):
                            break
            
            logger.info(f"Selected {len(frames_data)} high-quality frames from {len(high_quality_frames)} candidates")
            for i, frame in enumerate(frames_data):
                logger.info(f"Frame {i+1}: time={frame['time_ms']}ms, quality={frame.get('quality_score', 0):.3f}")
        
        # フレームデータをDBに保存
        frames = []
        for frame_data in frames_data:
            frame = Frame(
                video_id=video_id,
                time_ms=frame_data['time_ms'],
                sharpness=frame_data['sharpness'],
                brightness=frame_data['brightness'],
                contrast=frame_data['contrast'],
                phash=frame_data['phash'],
                frame_score=frame_data.get('quality_score', 0),  # quality_scoreを正しく参照
                frame_path=frame_data.get('frame_path', '')
            )
            
            # OCRテキストは後で処理されるため、ここでは設定しない
            # OCR処理は各フレームごとに個別に実行される
            
            db.add(frame)
            frames.append(frame)
        
        # 品質ベースのフレーム選択
        logger.info(f"Total frames available: {len(frames)}")
        
        # 品質スコアでソート
        frames_by_quality = sorted(frames, key=lambda x: x.frame_score or 0, reverse=True)
        
        # 品質閾値を設定（動的調整）
        if frames_by_quality:
            # 上位フレームの品質スコアから閾値を決定
            top_scores = [f.frame_score for f in frames_by_quality[:10]]
            avg_top_score = sum(top_scores) / len(top_scores) if top_scores else 0
            quality_threshold = max(0.25, avg_top_score * 0.6)  # 上位平均の60%または0.25の大きい方
            logger.info(f"Quality threshold set to {quality_threshold:.3f} (top avg: {avg_top_score:.3f})")
        else:
            quality_threshold = 0.25
        
        # 高品質フレームのみ選択
        selected_frames = []
        used_time_windows = []  # 既に選択されたフレームの時間範囲
        
        for frame in frames_by_quality:
            # 品質チェック
            if frame.frame_score < quality_threshold and len(selected_frames) >= 5:
                # 最低5枚確保したら、品質が低いフレームはスキップ
                continue
            
            # 時間的重複チェック（3秒以内に他のフレームがあればスキップ）
            frame_time = frame.time_ms
            is_too_close = False
            
            for selected in selected_frames:
                if abs(selected.time_ms - frame_time) < 3000:  # 3秒以内
                    is_too_close = True
                    break
            
            if not is_too_close:
                selected_frames.append(frame)
                frame.is_best = True
                logger.info(f"Selected frame at {frame_time}ms with quality {frame.frame_score:.3f}")
                
                # 十分な数のフレームを選択したら終了
                if len(selected_frames) >= min(15, len(frames_by_quality)):
                    break
        
        # 最低限のフレーム数を確保
        if len(selected_frames) < 3:
            logger.warning(f"Only {len(selected_frames)} frames selected, adding top quality frames")
            for frame in frames_by_quality[:5]:
                if frame not in selected_frames:
                    selected_frames.append(frame)
                    frame.is_best = True
        
        # 時間順にソート
        selected_frames = sorted(selected_frames, key=lambda x: x.time_ms)
        logger.info(f"Selected {len(selected_frames)} frames for analysis")
        
        # 均等に分散されたフレームからレシートデータを抽出
        logger.info(f"Processing {len(selected_frames)} evenly distributed frames")
        receipts_found = 0
        
        for idx, best_frame in enumerate(selected_frames):
            update_progress(50 + (20 * idx // len(selected_frames)), f"レシート {idx+1}/{len(selected_frames)} 分析中...")
            logger.info(f"Analyzing frame {idx+1}/{len(selected_frames)} at {best_frame.time_ms}ms")
            
            # Gemini APIで領収書データ抽出
            receipt_data = await analyzer.extract_receipt_data(
                best_frame.frame_path,
                best_frame.ocr_text or ''
            )
            
            # レシートデータ検証強化（過剰生成防止）
            if receipt_data and receipt_data.get('vendor'):
                # 1. 基本フィールド有効性検査
                vendor = receipt_data.get('vendor', '').strip()
                total = receipt_data.get('total', 0)
                
                # 2. 最小品質基準チェック - 緩和版
                # 販売店名検証（極端に無効なケースのみ除外）
                invalid_vendors = ['sample', 'test', 'unknown', 'ocr failed', 'sample store']
                vendor_normalized = vendor.lower().replace(' ', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                
                # 数字のみの販売店名を除外
                vendor_clean = vendor.replace(' ', '').replace('/', '').replace('-', '')
                if vendor_clean.isdigit():
                    logger.warning(f"Vendor name is all digits, skipping: {vendor}")
                    continue
                
                # ラインアイテム有効性チェック
                line_items = receipt_data.get('line_items', [])
                valid_line_items = [item for item in line_items if item and item.get('name') and item.get('name') != '不明']
                
                # より厳格な条件：金額があり、極端に無効でなければ保存
                if (len(vendor) < 1 or  # 販売店名が空
                    any(invalid in vendor_normalized for invalid in invalid_vendors) or  # 明らかに無効な販売店
                    not total or total <= 0 or  # 金額がないか0円
                    total > 10000000):  # 非現実的に大きい金額（1000万円超）
                    logger.error(f"Invalid receipt data detected: vendor='{vendor}', total={total}")
                    logger.info(f"Skipping low-quality receipt: vendor='{vendor}', total={total}, valid_items={len(valid_line_items)}")
                    continue
                
                # ベンダー名が"Unknown"で金額も0の場合もスキップ
                if vendor == 'Unknown' and total <= 0:
                    logger.error(f"Unknown vendor with zero amount, skipping")
                    continue
                
                # Debug: Log the raw receipt data
                logger.info(f"Raw receipt_data from analyzer: {receipt_data}")
                logger.info(f"Document type before DB save: '{receipt_data.get('document_type')}'")
                
                # issue_date を datetime オブジェクトに変換
                from datetime import datetime
                issue_date_value = receipt_data.get('issue_date')
                if issue_date_value:
                    if isinstance(issue_date_value, str):
                        try:
                            # YYYY-MM-DD 形式の文字列を datetime に変換
                            issue_date_value = datetime.strptime(issue_date_value, '%Y-%m-%d')
                        except ValueError:
                            logger.warning(f"Invalid date format: {issue_date_value}, using current date")
                            issue_date_value = datetime.now()
                    elif not isinstance(issue_date_value, datetime):
                        issue_date_value = datetime.now()
                else:
                    issue_date_value = datetime.now()
                
                # Final safety check for composite document types
                doc_type = receipt_data.get('document_type')
                if doc_type and '・' in doc_type:
                    doc_type = doc_type.split('・')[0]
                    logger.warning(f"Composite document type detected at Receipt creation: '{receipt_data.get('document_type')}' -> '{doc_type}'")
                else:
                    doc_type = receipt_data.get('document_type')
                
                # 最終チェック：ベンダー名が数字のみの場合はUnknownに変更
                if vendor and vendor.replace(' ', '').replace('/', '').replace('-', '').isdigit():
                    logger.warning(f"Vendor name is numeric, changing to Unknown: {vendor}")
                    receipt_data['vendor'] = 'Unknown'
                    vendor = 'Unknown'
                
                # レシート固有フィンガープリント生成および保存
                receipt_fingerprint = analyzer.generate_receipt_fingerprint(receipt_data)
                
                receipt = Receipt(
                    video_id=video_id,
                    best_frame_id=best_frame.id,
                    vendor=receipt_data.get('vendor'),
                    vendor_norm=analyzer._normalize_text(receipt_data.get('vendor', '')),
                    document_type=doc_type,
                    issue_date=issue_date_value,
                    currency=receipt_data.get('currency', 'JPY'),
                    total=receipt_data.get('total'),
                    subtotal=receipt_data.get('subtotal'),
                    tax=receipt_data.get('tax'),
                    tax_rate=receipt_data.get('tax_rate'),
                    payment_method=receipt_data.get('payment_method'),
                    memo=receipt_data.get('memo')
                )
                
                # メモは空にするか簡単な情報のみ
                receipt.memo = receipt_data.get('memo', '') or ''
                
                # スマート重複チェック - 現在のビデオ内でのみ比較
                existing_receipts = db.query(Receipt).filter(Receipt.video_id == video_id).all()
                duplicate_id = analyzer.check_duplicate(
                    best_frame.phash,
                    best_frame.ocr_text or '',
                    [{
                        'id': r.id, 
                        'phash': r.best_frame.phash if r.best_frame else None,
                        'normalized_text_hash': r.normalized_text_hash,
                        'time_ms': r.best_frame.time_ms if r.best_frame else None,
                        'vendor': r.vendor,
                        'total': r.total,
                        'issue_date': r.issue_date.isoformat() if r.issue_date else None
                    } for r in existing_receipts],
                    current_frame_time_ms=best_frame.time_ms,
                    current_receipt_data=receipt_data
                )
                
                if duplicate_id:
                    receipt.duplicate_of_id = duplicate_id
                    logger.info(f"重複検出: Receipt {duplicate_id}")
                    # 重複と判定された場合は保存せずにスキップ
                    receipts_found += 0  # 重複はカウントしない
                    logger.info(f"Skipping duplicate receipt, referencing existing #{duplicate_id}")
                    continue
                
                # 重複でない場合のみ保存
                try:
                    db.add(receipt)
                    db.commit()
                    db.refresh(receipt)
                    receipts_found += 1
                    logger.info(f"New receipt saved #{receipts_found}: {receipt.vendor} - ¥{receipt.total}")
                except Exception as e:
                    db.rollback()
                    # UNIQUE制約違反時は固有suffixを追加して再試行
                    import time
                    import random
                    unique_suffix = f"_{video_id}_{best_frame.time_ms}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                    receipt.vendor_norm = analyzer._normalize_text(receipt_data.get('vendor', '')) + unique_suffix
                    
                    try:
                        db.add(receipt)
                        db.commit()
                        db.refresh(receipt)
                        receipts_found += 1
                        logger.info(f"Receipt saved with unique suffix #{receipts_found}: {receipt.vendor} - ¥{receipt.total}")
                    except Exception as e2:
                        db.rollback()
                        logger.error(f"Failed to save receipt even with unique suffix: {e2}")
                        # 最終失敗時にも既存レシートがあるか確認
                        existing = db.query(Receipt).filter(
                            Receipt.vendor == receipt.vendor,
                            Receipt.issue_date == receipt.issue_date,
                            Receipt.total == receipt.total
                        ).first()
                        if existing:
                            receipt = existing
                            logger.info(f"Using existing receipt: Receipt {existing.id}")
                        else:
                            continue
                
                update_progress(70, "仕訳生成中...")
                
                # 仕訳自動生成
                if not duplicate_id:
                    generator = JournalGenerator(db)
                    journal_entries = generator.generate_journal_entries(receipt)
                    
                    for entry_data in journal_entries:
                        journal_entry = JournalEntry(
                            receipt_id=entry_data.receipt_id,
                            video_id=entry_data.video_id,
                            time_ms=int(entry_data.time_ms) if entry_data.time_ms is not None else 0,
                            debit_account=entry_data.debit_account,
                            credit_account=entry_data.credit_account,
                            debit_amount=entry_data.debit_amount,
                            credit_amount=entry_data.credit_amount,
                            tax_account=entry_data.tax_account,
                            tax_amount=entry_data.tax_amount,
                            memo=entry_data.memo,
                            status='unconfirmed'
                        )
                        db.add(journal_entry)
                        db.commit()
        
        # 新システムを使用していない場合のみここに到達
        if not selected_frames_new:
            update_progress(90, "処理完了中...")
            
            # ステータス更新
            video.status = "done"
            video.progress = 100
            video.progress_message = "分析完了"
            db.commit()
            
            logger.info(f"動画分析完了: Video {video_id}, Found {receipts_found} receipts from {len(selected_frames)} frames")
        
    except Exception as e:
        logger.error(f"動画分析エラー: {e}")
        video = db.query(Video).filter(Video.id == video_id).first()
        video.status = "error"
        video.error_message = str(e)
        db.commit()

@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """動画詳細取得"""
    try:
        # receipts、best_frame、history、journal_entries関係を一緒にロード
        video = db.query(Video).options(
            joinedload(Video.receipts).joinedload(Receipt.best_frame),
            joinedload(Video.receipts).joinedload(Receipt.history),
            joinedload(Video.journal_entries)  # 仕訳データも読み込む
        ).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(404, "動画が見つかりません")
        
        # 権限チェック: ログインユーザーは自分の動画のみ、未ログインはuser_idがNULLの動画のみ
        if current_user:
            if video.user_id != current_user.id:
                raise HTTPException(403, "この動画にアクセスする権限がありません")
        else:
            if video.user_id is not None:
                raise HTTPException(403, "この動画にアクセスする権限がありません")
        
        # レシートをフレーム時間順にソート
        if video.receipts:
            try:
                video.receipts.sort(key=lambda r: r.best_frame.time_ms if r.best_frame else 0)
            except Exception as e:
                logger.warning(f"レシートソートエラー: {e}")
                # ソートできない場合はそのまま返す
        
        # frames、receipts、journal_entries属性が存在しない場合は空リストを設定
        if not hasattr(video, 'frames'):
            video.frames = []
        if not hasattr(video, 'receipts'):
            video.receipts = []
        if not hasattr(video, 'journal_entries'):
            video.journal_entries = []
        
        return video
    except HTTPException:
        raise  # HTTPExceptionはそのまま再送出
    except Exception as e:
        logger.error(f"動画詳細取得エラー (video_id={video_id}): {e}", exc_info=True)
        raise HTTPException(500, f"動画詳細の取得に失敗しました: {str(e)}")

@router.get("/{video_id}/frame/{ms}")
async def get_frame(video_id: int, ms: int, db: Session = Depends(get_db)):
    """指定時刻のフレーム画像取得"""
    frame = db.query(Frame).filter(
        Frame.video_id == video_id,
        Frame.time_ms == ms
    ).first()
    
    if not frame or not frame.frame_path:
        raise HTTPException(404, "フレームが見つかりません")
    
    # Render環境での実際のファイルパス取得
    actual_frame_path = frame.frame_path
    if os.getenv("RENDER") == "true" and actual_frame_path.startswith("uploads/"):
        actual_frame_path = actual_frame_path.replace("uploads/", "/tmp/")
    
    if not os.path.exists(actual_frame_path):
        raise HTTPException(404, "フレーム画像ファイルが見つかりません")
    
    return FileResponse(actual_frame_path, media_type="image/jpeg")

@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """動画一覧取得"""
    try:
        # ユーザーがログインしている場合は自分の動画のみ、そうでない場合は全て
        query = db.query(Video)
        if current_user:
            query = query.filter(Video.user_id == current_user.id)
        else:
            # 未ログインユーザーは user_id が NULL の動画のみ
            query = query.filter(Video.user_id == None)
        
        # 最新のビデオが先に来るようにソート
        videos = query.order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
        
        # 各ビデオにレシート数を追加（自動/手動区分）
        for video in videos:
            try:
                total_receipts = db.query(Receipt).filter(Receipt.video_id == video.id).all()
                video.receipts_count = len(total_receipts)
                video.auto_receipts_count = len([r for r in total_receipts if not r.is_manual])
                video.manual_receipts_count = len([r for r in total_receipts if r.is_manual])
            except Exception as e:
                logger.error(f"レシート数取得エラー (video_id={video.id}): {e}")
                # エラー時はデフォルト値を設定
                video.receipts_count = 0
                video.auto_receipts_count = 0
                video.manual_receipts_count = 0
        
        return videos
    except Exception as e:
        logger.error(f"動画一覧取得エラー: {e}", exc_info=True)
        # エラー時は空のリストを返す
        return []

@router.get("/frames/{frame_id}/image")
async def get_frame_image(frame_id: int, db: Session = Depends(get_db)):
    """フレーム画像を取得"""
    frame = db.query(Frame).filter(Frame.id == frame_id).first()
    if not frame or not frame.frame_path:
        raise HTTPException(404, "フレームが見つかりません")
    
    # Render環境での実際のファイルパス取得
    actual_frame_path = frame.frame_path
    if os.getenv("RENDER") == "true" and actual_frame_path.startswith("uploads/"):
        actual_frame_path = actual_frame_path.replace("uploads/", "/tmp/")
    
    if not os.path.exists(actual_frame_path):
        logger.error(f"Frame image not found: {actual_frame_path} (original: {frame.frame_path})")
        raise HTTPException(404, "画像ファイルが見つかりません")
    
    return FileResponse(actual_frame_path, media_type="image/jpeg")

@router.get("/{video_id}/frame-at-time")
async def get_frame_at_time(
    video_id: int,
    time_ms: int = Query(..., description="時刻（ミリ秒）"),
    db: Session = Depends(get_db)
):
    """指定時刻のフレーム画像を取得（動画から直接抽出）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    # Render環境での実際のファイルパス取得
    video_path = video.local_path
    if os.getenv("RENDER") == "true" and video_path.startswith("uploads/"):
        video_path = video_path.replace("uploads/", "/tmp/")
    
    if not os.path.exists(video_path):
        raise HTTPException(404, "動画ファイルが見つかりません")
    
    # OpenCVで動画から指定時刻のフレームを抽出
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # フレーム番号を計算 (最小値0、最大値はtotal_frames-1)
    target_frame = max(0, min(int(time_ms * fps / 1000.0), total_frames - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    
    ret, frame = cap.read()
    
    # 実際に取得したフレームの時刻を計算
    actual_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
    actual_time_ms = int(actual_frame * 1000.0 / fps)
    
    cap.release()
    
    if not ret:
        raise HTTPException(404, "フレームを取得できませんでした")
    
    # フレームをJPEGに変換してメモリ上で処理
    import io
    from PIL import Image
    
    # BGRからRGBに変換
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    
    # JPEGバッファを作成
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=85)
    img_byte_arr.seek(0)
    
    # StreamingResponseで画像を返す
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        img_byte_arr, 
        media_type="image/jpeg",
        headers={
            "X-Frame-Time": str(actual_time_ms),
            "X-Requested-Time": str(time_ms)
        }
    )

@router.get("/{video_id}/thumbnail")
async def get_video_thumbnail(video_id: int, db: Session = Depends(get_db)):
    """ビデオサムネイル提供"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    # Render環境での実際のファイルパス取得
    actual_thumbnail_path = video.thumbnail_path
    if os.getenv("RENDER") == "true" and actual_thumbnail_path and actual_thumbnail_path.startswith("uploads/"):
        actual_thumbnail_path = actual_thumbnail_path.replace("uploads/", "/tmp/")
    
    actual_video_path = video.local_path
    if os.getenv("RENDER") == "true" and actual_video_path.startswith("uploads/"):
        actual_video_path = actual_video_path.replace("uploads/", "/tmp/")
    
    # サムネイルがなければ生成を試みる
    if not actual_thumbnail_path or not os.path.exists(actual_thumbnail_path):
        # 動的にサムネイル生成
        if actual_video_path and os.path.exists(actual_video_path):
            try:
                import cv2
                # Render環境では/tmpを使用
                if os.getenv("RENDER") == "true":
                    thumbnail_dir = Path("/tmp/thumbnails")
                else:
                    thumbnail_dir = Path("uploads/thumbnails")
                thumbnail_dir.mkdir(parents=True, exist_ok=True)
                thumbnail_filename = f"{Path(actual_video_path).stem}_thumb.jpg"
                thumbnail_path = thumbnail_dir / thumbnail_filename
                
                cap = cv2.VideoCapture(actual_video_path)
                cap.set(cv2.CAP_PROP_POS_FRAMES, 10)
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                
                if ret:
                    height, width = frame.shape[:2]
                    new_width = 320
                    new_height = int(height * (new_width / width))
                    resized = cv2.resize(frame, (new_width, new_height))
                    cv2.imwrite(str(thumbnail_path), resized)
                    
                    # DBアップデート - Render環境では uploads パスとして保存
                    if os.getenv("RENDER") == "true":
                        db_thumbnail_path = str(thumbnail_path).replace("/tmp/", "uploads/")
                    else:
                        db_thumbnail_path = str(thumbnail_path)
                    video.thumbnail_path = db_thumbnail_path
                    db.commit()
                    
                cap.release()
                return FileResponse(str(thumbnail_path), media_type="image/jpeg")
            except Exception as e:
                logger.error(f"Thumbnail generation failed: {e}")
        
        # デフォルト画像を返すか404
        raise HTTPException(404, "サムネイルが見つかりません")
    
    return FileResponse(actual_thumbnail_path, media_type="image/jpeg")

@router.post("/{video_id}/analyze-frame-preview")
async def analyze_frame_preview(
    video_id: int,
    time_ms: int,
    db: Session = Depends(get_db)
):
    """特定時刻のフレームを分析（プレビューのみ、保存しない）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    try:
        analyzer = VideoAnalyzer()
        
        # 指定時刻のフレームを抽出
        cap = cv2.VideoCapture(video.local_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        
        target_frame = int(time_ms * fps / 1000.0)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        actual_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        actual_time_ms = int(actual_frame * 1000.0 / fps)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise HTTPException(400, "フレームを取得できませんでした")
        
        # フレームを一時ファイルとして保存
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            cv2.imwrite(tmp.name, frame)
            temp_path = tmp.name
        
        try:
            # OCR分析を実行（保存はしない）
            receipt_data = await analyzer.extract_receipt_data(temp_path, '')
            
            # 一時ファイルを削除
            os.unlink(temp_path)
            
            if receipt_data:
                return {
                    "success": True,
                    "receipt_data": receipt_data,
                    "time_ms": actual_time_ms
                }
            else:
                return {
                    "success": False,
                    "message": "領収書データを抽出できませんでした",
                    "time_ms": actual_time_ms
                }
        finally:
            # 一時ファイルのクリーンアップ
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"Frame preview analysis error: {e}")
        raise HTTPException(500, f"分析に失敗しました: {str(e)}")

@router.post("/{video_id}/analyze-frame")
async def analyze_frame_at_time(
    video_id: int,
    time_ms: int,
    db: Session = Depends(get_db)
):
    """特定時刻のフレームを手動で分析（データベースに保存）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    try:
        analyzer = VideoAnalyzer()
        
        # 指定時刻のフレームを抽出
        import cv2
        cap = cv2.VideoCapture(video.local_path)
        
        # ビデオのFPSを取得
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30  # デフォルトFPS
        
        # ミリ秒からフレーム番号を計算
        target_frame = int(time_ms * fps / 1000.0)
        
        # フレーム番号でシーク
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        # 実際のフレーム位置を取得
        actual_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        
        # 重要: CAP_PROP_POS_MSECは信頼できないので、フレーム番号から計算
        actual_time_ms = int(actual_frame * 1000.0 / fps)
        
        ret, frame = cap.read()
        
        if not ret:
            # フレーム番号でのシークが失敗した場合、順次読み込みを試す
            logger.warning(f"Frame seek failed at frame {target_frame}, trying sequential read")
            cap.release()
            cap = cv2.VideoCapture(video.local_path)
            
            # 目標フレームまで順次読み込み
            frame = None
            for i in range(target_frame + 1):
                ret, temp_frame = cap.read()
                if not ret:
                    break
                if i == target_frame:
                    frame = temp_frame
                    actual_frame = i
                    actual_time_ms = int(i * 1000.0 / fps)
                    break
            
            if frame is None:
                cap.release()
                raise HTTPException(400, f"指定時刻 {time_ms}ms のフレームを取得できません")
        
        # フレームを保存（実際の時刻を使用）
        # フレーム品質向上処理
        height, width = frame.shape[:2]
        
        # 最小解像度確保（OCR用）
        MIN_WIDTH = 1500  # OCR用最小幅
        if width < MIN_WIDTH:
            scale_factor = MIN_WIDTH / width
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            # INTER_CUBIC補間で高品質アップスケール
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            logger.info(f"Frame upscaled from {width}x{height} to {new_width}x{new_height} for better OCR")
        
        # コントラスト強化
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        frame = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        
        # Render環境でのフレーム保存パス
        frame_filename = f"manual_frame_{video_id}_{actual_time_ms}.jpg"
        if os.getenv("RENDER") == "true":
            actual_frame_path = f"/tmp/frames/{frame_filename}"
            db_frame_path = f"uploads/frames/{frame_filename}"
        else:
            actual_frame_path = f"uploads/frames/{frame_filename}"
            db_frame_path = actual_frame_path
        
        # ディレクトリ確認
        os.makedirs(os.path.dirname(actual_frame_path), exist_ok=True)
        cv2.imwrite(actual_frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 100])  # 最高品質で保存
        cap.release()
        
        # Supabase Storageにフレームをアップロード
        if use_cloud_storage and storage_service:
            try:
                with open(actual_frame_path, 'rb') as f:
                    frame_content = f.read()
                
                # クラウドパス生成
                cloud_frame_path = storage_service.generate_file_path(
                    user_id=video.user_id if video.user_id else 1,  # VideoのユーザーIDを使用
                    filename=frame_filename,
                    file_type="frame"
                )
                
                success, frame_cloud_url = storage_service.upload_file_sync(
                    file_content=frame_content,
                    file_path=cloud_frame_path,
                    content_type="image/jpeg"
                )
                
                if success:
                    logger.info(f"Frame uploaded to cloud: {frame_cloud_url}")
                    db_frame_path = frame_cloud_url
            except Exception as e:
                logger.warning(f"Failed to upload frame to cloud: {e}")
        
        logger.info(f"Frame capture - Requested: {time_ms}ms (frame {target_frame}), Actual: {actual_time_ms}ms (frame {actual_frame}), FPS: {fps}")
        
        # フレーム品質分析（実際の時刻を使用）
        frame_data = analyzer._analyze_frame(actual_frame_path, actual_time_ms)
        
        # フレームをDBに保存（実際の時刻を使用）
        frame_obj = Frame(
            video_id=video_id,
            time_ms=actual_time_ms,  # 実際の時刻を保存
            sharpness=frame_data['sharpness'],
            brightness=frame_data['brightness'],
            contrast=frame_data['contrast'],
            phash=frame_data['phash'],
            frame_score=frame_data['frame_score'],
            frame_path=db_frame_path,
            is_best=True,  # 手動選択フレームは常にベスト扱い
            is_manual=True  # 手動追加フラグ
        )
        db.add(frame_obj)
        db.commit()
        db.refresh(frame_obj)
        
        # Gemini APIで領収書データ抽出
        receipt_data = await analyzer.extract_receipt_data(frame_path, '')
        
        if receipt_data:
            # Final safety check for composite document types
            doc_type = receipt_data.get('document_type')
            if doc_type and '・' in doc_type:
                doc_type = doc_type.split('・')[0]
                logger.warning(f"Manual frame - Composite type detected: '{receipt_data.get('document_type')}' -> '{doc_type}'")
            
            payment_method = receipt_data.get('payment_method')
            
            from datetime import datetime
            issue_date_value = receipt_data.get('issue_date')
            if issue_date_value:
                if isinstance(issue_date_value, str):
                    try:
                        issue_date_value = datetime.strptime(issue_date_value, '%Y-%m-%d')
                    except ValueError:
                        issue_date_value = datetime.now()
                elif not isinstance(issue_date_value, datetime):
                    issue_date_value = datetime.now()
            else:
                issue_date_value = datetime.now()
            
            # 手動追加は重複チェックなしで常に新しいレシートを生成
            # タイムスタンプを追加してUNIQUE制約を回避
            import time
            unique_suffix = f"_manual_{actual_time_ms}_{int(time.time() * 1000)}"
            
            receipt = Receipt(
                video_id=video_id,
                best_frame_id=frame_obj.id,
                vendor=receipt_data.get('vendor'),
                # vendor_normに固有suffixを追加してUNIQUE制約を回避
                vendor_norm=analyzer._normalize_text(receipt_data.get('vendor', '')) + unique_suffix,
                document_type=doc_type,
                issue_date=issue_date_value,
                currency=receipt_data.get('currency', 'JPY'),
                total=receipt_data.get('total'),
                subtotal=receipt_data.get('subtotal'),
                tax=receipt_data.get('tax'),
                tax_rate=receipt_data.get('tax_rate'),
                payment_method=payment_method,
                memo=f"手動追加 ({actual_time_ms}ms)",
                is_manual=True
            )
                
            try:
                db.add(receipt)
                db.commit()
                db.refresh(receipt)
                logger.info(f"New manual receipt created: {receipt.id}")
            except Exception as e:
                db.rollback()
                logger.error(f"Manual receipt save error: {e}")
                # それでもエラーが発生した場合は現在時刻ベースでより固有なsuffixを生成
                import time
                import random
                unique_suffix = f"_manual_{actual_time_ms}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                receipt.vendor_norm = analyzer._normalize_text(receipt_data.get('vendor', '')) + unique_suffix
                receipt.memo = f"手動追加 ({actual_time_ms}ms) - 再試行"
                
                try:
                    db.add(receipt)
                    db.commit()
                    db.refresh(receipt)
                    logger.info(f"Manual receipt created with adjusted time: {receipt.id}")
                except Exception as e2:
                    db.rollback()
                    logger.error(f"Second attempt failed: {e2}")
                    raise HTTPException(500, f"領収書の保存に失敗しました: {str(e2)}")
            
            # 仕訳自動生成（手動追加は常に新しいレシートなので）
            generator = JournalGenerator(db)
            journal_entries = generator.generate_journal_entries(receipt)
            
            for entry_data in journal_entries:
                journal_entry = JournalEntry(
                    receipt_id=entry_data.receipt_id,
                    video_id=entry_data.video_id,
                    time_ms=int(entry_data.time_ms) if entry_data.time_ms is not None else 0,
                    debit_account=entry_data.debit_account,
                    credit_account=entry_data.credit_account,
                    debit_amount=entry_data.debit_amount,
                    credit_amount=entry_data.credit_amount,
                    tax_account=entry_data.tax_account,
                    tax_amount=entry_data.tax_amount,
                    memo=entry_data.memo,
                    status='unconfirmed'
                )
                db.add(journal_entry)
            
            db.commit()
            
            return {
                "message": "フレーム分析完了",
                "frame_id": frame_obj.id,
                "receipt_id": receipt.id,
                "time_ms": actual_time_ms,  # 実際の時刻を返す
                "requested_time_ms": time_ms,  # 要求された時刻も参考に
                "frame_score": frame_data['frame_score'],
                "receipt_data": receipt_data,
                "receipt": {
                    "id": receipt.id,
                    "vendor": receipt.vendor,
                    "total": receipt.total,
                    "tax": receipt.tax,
                    "issue_date": receipt.issue_date.isoformat() if receipt.issue_date else None,
                    "payment_method": receipt.payment_method,
                    "memo": receipt.memo
                }
            }
        else:
            return {
                "message": "領収書データを抽出できませんでした",
                "frame_id": frame_obj.id,
                "time_ms": actual_time_ms,  # 実際の時刻を返す
                "requested_time_ms": time_ms,  # 要求された時刻も参考に
                "frame_score": frame_data['frame_score']
            }
            
    except Exception as e:
        logger.error(f"手動フレーム分析エラー: {e}")
        raise HTTPException(500, f"分析に失敗しました: {str(e)}")

@router.post("/{video_id}/receipts/{receipt_id}/update-frame")
async def update_receipt_frame(
    video_id: int,
    receipt_id: int,
    time_ms: int,
    db: Session = Depends(get_db)
):
    """レシートのフレームを更新（OCR再分析後に適用時）"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.video_id == video_id
    ).first()
    
    if not receipt:
        raise HTTPException(404, "領収書が見つかりません")
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    try:
        # 新しいフレームを抽出して保存
        cap = cv2.VideoCapture(video.local_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        
        target_frame = int(time_ms * fps / 1000.0)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        actual_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        actual_time_ms = int(actual_frame * 1000.0 / fps)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise HTTPException(400, "フレームを取得できませんでした")
        
        # フレームを保存
        import time
        timestamp = int(time.time() * 1000)
        frame_filename = f"{timestamp}_frame_{actual_time_ms:08d}ms.jpg"
        
        # Render環境でのパス設定
        if os.getenv("RENDER") == "true":
            output_dir = Path("/tmp/frames")
            actual_frame_path = str(output_dir / frame_filename)
            db_frame_path = f"uploads/frames/{frame_filename}"
        else:
            output_dir = Path("uploads/frames")
            actual_frame_path = str(output_dir / frame_filename)
            db_frame_path = actual_frame_path
        
        output_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(actual_frame_path, frame)
        
        # Supabase Storageにフレームをアップロード
        if use_cloud_storage and storage_service:
            try:
                with open(actual_frame_path, 'rb') as f:
                    frame_content = f.read()
                
                # クラウドパス生成
                cloud_frame_path = storage_service.generate_file_path(
                    user_id=video.user_id if video.user_id else 1,  # VideoのユーザーIDを使用
                    filename=frame_filename,
                    file_type="frame"
                )
                
                success, frame_cloud_url = storage_service.upload_file_sync(
                    file_content=frame_content,
                    file_path=cloud_frame_path,
                    content_type="image/jpeg"
                )
                
                if success:
                    logger.info(f"Frame uploaded to cloud: {frame_cloud_url}")
                    db_frame_path = frame_cloud_url
            except Exception as e:
                logger.warning(f"Failed to upload frame to cloud: {e}")
        
        # 画像分析（品質スコア、pHash等）
        analyzer = VideoAnalyzer()
        frame_data = analyzer._analyze_frame(actual_frame_path, actual_time_ms)
        
        # 新しいFrameオブジェクトを作成
        new_frame = Frame(
            video_id=video_id,
            time_ms=actual_time_ms,
            frame_path=db_frame_path,
            sharpness=frame_data['sharpness'],
            brightness=frame_data['brightness'],
            contrast=frame_data['contrast'],
            phash=frame_data['phash'],
            is_manual=True  # 手動で選択されたフレーム
        )
        db.add(new_frame)
        db.flush()  # IDを取得するため
        
        # 古いフレームのIDを保存（履歴用）
        old_frame_id = receipt.best_frame_id
        
        # 領収書のbest_frame_idを更新
        receipt.best_frame_id = new_frame.id
        
        # 履歴を記録
        history = ReceiptHistory(
            receipt_id=receipt_id,
            field_name="best_frame_id",
            old_value=str(old_frame_id) if old_frame_id else None,
            new_value=str(new_frame.id),
            changed_by="user_frame_update"
        )
        db.add(history)
        
        # updated_atを更新
        from datetime import datetime
        receipt.updated_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "フレームを更新しました",
            "new_frame_id": new_frame.id,
            "time_ms": actual_time_ms,
            "frame_url": f"/api/videos/frames/{new_frame.id}/image"
        }
        
    except Exception as e:
        logger.error(f"Frame update error: {e}")
        db.rollback()
        raise HTTPException(500, f"フレーム更新に失敗しました: {str(e)}")

@router.patch("/{video_id}/receipts/{receipt_id}")
async def update_receipt(
    video_id: int,
    receipt_id: int,
    update_data: ReceiptUpdate,
    db: Session = Depends(get_db)
):
    """レシート情報修正"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.video_id == video_id
    ).first()
    
    if not receipt:
        raise HTTPException(404, "領収書が見つかりません")
    
    # 変更事項追跡
    update_dict = update_data.dict(exclude_unset=True)
    for field, new_value in update_dict.items():
        old_value = getattr(receipt, field)
        
        # 値が実際に変更された場合のみ履歴保存
        if old_value != new_value:
            # 履歴記録
            history = ReceiptHistory(
                receipt_id=receipt_id,
                field_name=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
                changed_by="user"
            )
            db.add(history)
            
            # レシート更新
            setattr(receipt, field, new_value)
    
    # vendorが変更された場合、vendor_normも更新
    if 'vendor' in update_dict:
        analyzer = VideoAnalyzer()
        receipt.vendor_norm = analyzer._normalize_text(update_dict['vendor'] or '')
    
    # updated_at更新
    from datetime import datetime
    receipt.updated_at = datetime.now()
    
    db.commit()
    db.refresh(receipt)
    
    # 履歴と一緒に返す
    receipt_with_history = db.query(Receipt).options(
        joinedload(Receipt.history),
        joinedload(Receipt.best_frame)
    ).filter(Receipt.id == receipt_id).first()
    
    # 履歴をシリアライズ可能な形式に変換
    history_data = []
    for h in receipt_with_history.history:
        history_data.append({
            "id": h.id,
            "field_name": h.field_name,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "changed_by": h.changed_by,
            "changed_at": h.changed_at.isoformat() if h.changed_at else None
        })
    
    return {
        "message": "領収書を更新しました",
        "receipt_id": receipt_with_history.id,
        "history": history_data
    }

@router.get("/{video_id}/receipts/{receipt_id}/history")
async def get_receipt_history(
    video_id: int,
    receipt_id: int,
    db: Session = Depends(get_db)
):
    """レシート修正履歴照会"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.video_id == video_id
    ).first()
    
    if not receipt:
        raise HTTPException(404, "領収書が見つかりません")
    
    history = db.query(ReceiptHistory).filter(
        ReceiptHistory.receipt_id == receipt_id
    ).order_by(ReceiptHistory.changed_at.desc()).all()
    
    return history

@router.delete("/{video_id}/receipts/{receipt_id}")
async def delete_receipt(
    video_id: int,
    receipt_id: int,
    db: Session = Depends(get_db)
):
    """レシート削除"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.video_id == video_id
    ).first()
    
    if not receipt:
        raise HTTPException(404, "領収書が見つかりません")
    
    # 関連する仕訳も削除 (CASCADE設定がある場合は自動削除)
    db.query(JournalEntry).filter(JournalEntry.receipt_id == receipt_id).delete()
    
    # 関連するフレーム（手動追加の場合）も削除
    if receipt.is_manual and receipt.best_frame_id:
        frame = db.query(Frame).filter(Frame.id == receipt.best_frame_id).first()
        if frame and frame.is_manual:
            # フレーム画像ファイルも削除
            if frame.frame_path and os.path.exists(frame.frame_path):
                try:
                    os.remove(frame.frame_path)
                except:
                    pass
            db.delete(frame)
    
    # 領収書削除
    db.delete(receipt)
    db.commit()
    
    return {"message": "領収書を削除しました", "receipt_id": receipt_id}

@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    """ビデオ削除（改善版）"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(404, "動画が見つかりません")
        
        # トランザクション開始
        try:
            # 関連データを正しい順序で削除
            # 1. JournalEntry（最も依存関係が深い）
            journal_count = db.query(JournalEntry).filter(JournalEntry.video_id == video_id).count()
            db.query(JournalEntry).filter(JournalEntry.video_id == video_id).delete(synchronize_session=False)
            logger.info(f"Deleted {journal_count} journal entries for video {video_id}")
            
            # 2. Receipt（Frameに依存）
            receipt_count = db.query(Receipt).filter(Receipt.video_id == video_id).count()
            db.query(Receipt).filter(Receipt.video_id == video_id).delete(synchronize_session=False)
            logger.info(f"Deleted {receipt_count} receipts for video {video_id}")
            
            # 3. Frame（Videoに依存）
            frame_count = db.query(Frame).filter(Frame.video_id == video_id).count()
            db.query(Frame).filter(Frame.video_id == video_id).delete(synchronize_session=False)
            logger.info(f"Deleted {frame_count} frames for video {video_id}")
            
            # 4. ローカルファイル削除（エラーは無視）
            if video.local_path:
                try:
                    # Render環境のパス変換
                    actual_path = video.local_path
                    if os.getenv("RENDER") == "true" and actual_path.startswith("uploads/"):
                        actual_path = actual_path.replace("uploads/", "/tmp/")
                    
                    if os.path.exists(actual_path):
                        os.remove(actual_path)
                        logger.info(f"Deleted file: {actual_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {video.local_path}: {e}")
                    # ファイル削除失敗は無視して続行
            
            # 5. ビデオレコード削除
            db.delete(video)
            
            # コミット
            db.commit()
            logger.info(f"Successfully deleted video {video_id}")
            
            return {"message": "動画を削除しました", "video_id": video_id}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting video {video_id}: {e}", exc_info=True)
            raise HTTPException(500, f"削除中にエラーが発生しました: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting video {video_id}: {e}", exc_info=True)
        raise HTTPException(500, f"予期しないエラーが発生しました: {str(e)}")

def extract_receipt_info_from_text(ocr_text: str) -> Optional[Dict[str, Any]]:
    """
    OCRテキストから領収書情報を抽出（改善版）
    発行元と宛名を正しく区別し、日付の精度を向上
    """
    import re
    from datetime import datetime
    
    if not ocr_text:
        return None
    
    receipt_info = {}
    
    # 改善版：発行元（店舗名）を正しく検出
    lines = ocr_text.split('\n')
    vendor_found = False
    
    # 宛名パターン（これらは除外）
    recipient_patterns = [r'様$', r'御中$', r'^\s*お客様', r'^\s*宛名']
    
    for i, line in enumerate(lines[:10]):  # 最初の10行をチェック
        line = line.strip()
        if not line or len(line) < 2:
            continue
        
        # 宛名行は除外
        is_recipient = any(re.search(pattern, line) for pattern in recipient_patterns)
        if is_recipient:
            continue
        
        # 住所や電話番号の前の行は店舗名の可能性が高い
        if i < len(lines) - 1:
            next_line = lines[i + 1].strip()
            if re.search(r'〒?\d{3}-?\d{4}|TEL|電話|☎', next_line):
                receipt_info['vendor'] = line[:50]
                vendor_found = True
                break
        
        # 店舗名パターンにマッチ
        if re.search(r'(店|ストア|マート|スーパー|センター|株式会社|有限会社|\(株\)|㈱)$', line):
            receipt_info['vendor'] = line[:50]
            vendor_found = True
            break
        
        # 最初の有効な行を暫定的に店舗名とする（数字のみの行は除外）
        if not vendor_found and not re.match(r'^[\d\s\-\/\.:]+$', line):
            receipt_info['vendor'] = line[:50]
            vendor_found = True  # 続けて探す
    
    # 合計金額を検出
    total_patterns = [
        r'合計[:\s]*[¥￥]?[\s]*([\d,]+)',
        r'合\s*計[:\s]*[¥￥]?[\s]*([\d,]+)',
        r'総額[:\s]*[¥￥]?[\s]*([\d,]+)',
        r'[¥￥]\s*([\d,]+)\s*円?',
        r'([\d,]+)\s*円'
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)
                if amount > 0 and amount < 10000000:  # 妥当な金額範囲
                    receipt_info['total'] = amount
                    break
            except:
                continue
    
    # 改善版：日付を正確に検出（このフレームの日付のみ）
    date_patterns = [
        # 完全な日付形式を優先
        (r'(\d{4})[年\-\/](\d{1,2})[月\-\/](\d{1,2})[日]?', 'full'),
        (r'令和(\d{1,2})年(\d{1,2})月(\d{1,2})日', 'reiwa'),
        (r'R(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{1,2})', 'reiwa_short'),
        (r'平成(\d{1,2})年(\d{1,2})月(\d{1,2})日', 'heisei'),
        (r'H(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{1,2})', 'heisei_short'),
        (r'(\d{2})[年\-\/](\d{1,2})[月\-\/](\d{1,2})', 'short_year'),
        (r'(\d{1,2})[月\/](\d{1,2})[日]?', 'month_day'),
    ]
    
    # 日付キーワード近くの日付を優先
    date_keywords = ['日付', '発行日', 'Date', '年月日', '取引日']
    found_dates = []
    
    for i, line in enumerate(lines[:20]):  # 最初の20行のみチェック
        line = line.strip()
        priority = 2 if any(kw in line for kw in date_keywords) else 1
        if i < 5:  # 上部の日付は優先度高
            priority += 1
        
        for pattern, date_type in date_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                try:
                    if date_type == 'full':
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    elif date_type == 'reiwa':
                        year, month, day = 2018 + int(match.group(1)), int(match.group(2)), int(match.group(3))
                    elif date_type == 'reiwa_short':
                        year, month, day = 2018 + int(match.group(1)), int(match.group(2)), int(match.group(3))
                    elif date_type == 'heisei':
                        year, month, day = 1988 + int(match.group(1)), int(match.group(2)), int(match.group(3))
                    elif date_type == 'heisei_short':
                        year, month, day = 1988 + int(match.group(1)), int(match.group(2)), int(match.group(3))
                    elif date_type == 'short_year':
                        year = 2000 + int(match.group(1))
                        month, day = int(match.group(2)), int(match.group(3))
                    elif date_type == 'month_day':
                        year = datetime.now().year
                        month, day = int(match.group(1)), int(match.group(2))
                    else:
                        continue
                    
                    # 妥当性チェック
                    if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        found_dates.append((priority, i, f"{year:04d}-{month:02d}-{day:02d}"))
                except:
                    continue
    
    # 最も優先度の高い日付を選択
    if found_dates:
        found_dates.sort(key=lambda x: (-x[0], x[1]))  # 優先度高、行番号小を優先
        receipt_info['date'] = found_dates[0][2]
    
    # 最低限の情報があれば返す
    if receipt_info.get('vendor') or receipt_info.get('total'):
        # デフォルト値を設定
        if not receipt_info.get('vendor'):
            receipt_info['vendor'] = 'レシート'
        if not receipt_info.get('total'):
            receipt_info['total'] = 0
        if not receipt_info.get('date'):
            receipt_info['date'] = None
            
        return receipt_info
    
    return None

def process_video_ocr_wrapper(video_id: int):
    """バックグラウンドタスク用のラッパー関数（超簡易版）"""
    logger.info(f"バックグラウンドタスク開始: Video ID {video_id}")
    
    # get_dbを使用してセッションを作成
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # すべての環境で完全なOCR処理を実行
        logger.info("完全OCR処理モード開始")
        process_video_ocr_sync(video_id, db)
        logger.info(f"バックグラウンドタスク完了: Video ID {video_id}")
    except Exception as e:
        logger.error(f"処理エラー: {e}", exc_info=True)
        # エラー状態を記録
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = "error"
                video.error_message = str(e)[:500]
                db.commit()
        except:
            db.rollback()
    finally:
        try:
            next(db_gen, None)  # ジェネレータを終了
        except:
            pass
        db.close()

def process_video_ocr_sync(video_id: int, db: Session):
    """
    実際のOCR処理を実行（同期版）
    Google Vision APIを使用して領収書を検出・認識
    """
    import time
    start_time = time.time()
    max_processing_time = 180  # 最大3分
    
    logger.info(f"OCR処理開始: Video ID {video_id}")
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            return
        
        # 進行状況更新
        video.status = "processing"
        video.progress = 20
        video.progress_message = "フレーム抽出中..."
        db.commit()
        
        # 必要なディレクトリを作成（Render環境を考慮）
        import os
        if os.getenv("RENDER") == "true":
            # Render環境では/tmpを使用
            frames_dir = Path("/tmp/frames")
        else:
            base_path = Path(os.path.dirname(os.path.abspath(__file__))).parent  # backend/
            frames_dir = base_path / "uploads" / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        # Vision OCRサービスを使用
        from services.vision_ocr import VisionOCRService
        ocr_service = VisionOCRService()
        
        # VideoAnalyzerインスタンス作成（領収書データ抽出用）
        analyzer = VideoAnalyzer()
        
        # 動画からフレーム抽出（2秒間隔）
        # Render環境での実際のビデオパス取得
        actual_video_path = video.local_path
        if os.getenv("RENDER") == "true" and actual_video_path.startswith("uploads/"):
            actual_video_path = actual_video_path.replace("uploads/", "/tmp/")
        
        # ビデオファイルの存在確認
        if not os.path.exists(actual_video_path):
            logger.error(f"Video file not found: {actual_video_path}")
            video.status = "error"
            video.error_message = f"ビデオファイルが見つかりません: {actual_video_path}"
            db.commit()
            return
        
        logger.info(f"Processing video at: {actual_video_path}")
        cap = cv2.VideoCapture(actual_video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Video info: {duration_sec:.1f}秒, {total_frames}フレーム, {fps:.1f}fps")
        
        # スマートフレーム抽出（品質ベース選別）
        extracted_frames = []
        max_final_frames = 15  # 最終的に処理する最大フレーム数
        sample_interval = 1.5  # 1.5秒ごとにサンプリング
        
        # 1. 初期サンプリング：1秒ごとにフレーム候補を収集
        candidate_frames = []
        for sec_float in [i * sample_interval for i in range(int(duration_sec / sample_interval) + 1)]:
            frame_number = int(sec_float * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret and frame is not None:
                # フレーム品質を評価
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 1. 鮮明度（ラプラシアン分散）
                laplacian = cv2.Laplacian(gray, cv2.CV_64F)
                sharpness = laplacian.var()
                
                # 2. 明るさ（平均輝度）
                brightness = gray.mean()
                
                # 3. コントラスト（標準偏差）
                contrast = gray.std()
                
                # 4. エッジ検出（テキスト存在の可能性）
                edges = cv2.Canny(gray, 50, 150)
                edge_density = edges.mean()
                
                # 総合スコア計算
                quality_score = (
                    sharpness * 0.4 +  # 鮮明度重視
                    (brightness / 255.0) * 100 * 0.2 +  # 適度な明るさ
                    contrast * 0.2 +  # コントラスト
                    edge_density * 0.2  # エッジ（テキストの可能性）
                )
                
                candidate_frames.append({
                    'frame': frame,
                    'time_ms': int(sec_float * 1000),
                    'quality_score': quality_score,
                    'sharpness': sharpness,
                    'brightness': brightness,
                    'contrast': contrast,
                    'phash': ''  # TODO: 後で実装
                })
        
        # 2. 品質順でソートし、重複を避けながら選別
        candidate_frames.sort(key=lambda x: x['quality_score'], reverse=True)
        
        selected_times = set()
        min_time_diff = 1500  # 最低1.5秒の間隔（処理速度改善）
        
        for candidate in candidate_frames:
            if len(extracted_frames) >= max_final_frames:
                break
                
            # 時間的に近いフレームが既に選ばれていないかチェック
            time_ms = candidate['time_ms']
            too_close = any(abs(time_ms - t) < min_time_diff for t in selected_times)
            
            if not too_close and candidate['quality_score'] > 10:  # 最低品質基準
                # フレーム保存
                frame_filename = f"frame_{video_id}_{time_ms:06d}.jpg"
                frame_path = str(frames_dir / frame_filename)
                cv2.imwrite(frame_path, candidate['frame'])
                
                # Supabase Storageにフレームをアップロード
                frame_cloud_url = frame_path  # デフォルトはローカルパス
                if use_cloud_storage and storage_service:
                    try:
                        # JPEGエンコード
                        _, buffer = cv2.imencode('.jpg', candidate['frame'], [cv2.IMWRITE_JPEG_QUALITY, 95])
                        frame_content = buffer.tobytes()
                        
                        # クラウドパス生成
                        cloud_frame_path = storage_service.generate_file_path(
                            user_id=1,  # TODO: 実際のユーザーIDを使用
                            filename=frame_filename,
                            file_type="frame"
                        )
                        
                        success, cloud_url = storage_service.upload_file_sync(
                            file_content=frame_content,
                            file_path=cloud_frame_path,
                            content_type="image/jpeg"
                        )
                        
                        if success:
                            logger.info(f"Frame uploaded to cloud: {cloud_url}")
                            frame_cloud_url = cloud_url
                    except Exception as e:
                        logger.warning(f"Failed to upload frame to cloud: {e}")
                
                extracted_frames.append({
                    'path': frame_path,
                    'frame_path': frame_cloud_url,  # クラウドURLまたはローカルパス
                    'time_ms': time_ms,
                    'quality_score': candidate['quality_score'],
                    'sharpness': candidate['sharpness'],
                    'brightness': candidate['brightness'],
                    'contrast': candidate['contrast'],
                    'phash': candidate['phash']
                })
                selected_times.add(time_ms)
        
        # 3. 時間順にソート
        extracted_frames.sort(key=lambda x: x['time_ms'])
        
        cap.release()
        logger.info(f"Extracted {len(extracted_frames)} frames")
        
        # 進行状況更新
        video.progress = 40
        video.progress_message = f"{len(extracted_frames)}枚のフレームをOCR処理中..."
        db.commit()
        
        # 各フレームをOCR処理
        receipts_found = 0
        for i, frame_info in enumerate(extracted_frames):
            # 処理時間チェック
            if time.time() - start_time > max_processing_time:
                logger.warning(f"Processing time limit reached ({max_processing_time}s), stopping at frame {i}/{len(extracted_frames)}")
                video.progress_message = f"時間制限により処理を終了: {receipts_found}件の領収書を検出"
                break
            
            try:
                # 進行状況更新
                progress = 40 + int(40 * i / len(extracted_frames))
                video.progress = progress
                video.progress_message = f"フレーム {i+1}/{len(extracted_frames)} 分析中..."
                db.commit()
                
                # フレームファイルの存在確認
                if not os.path.exists(frame_info['path']):
                    logger.error(f"Frame file not found: {frame_info['path']}")
                    continue
                
                # Vision APIでOCR実行
                logger.info(f"OCR processing frame: {frame_info['path']}")
                ocr_result = ocr_service.extract_text_from_image(frame_info['path'])
                ocr_text = ocr_result.get('full_text', '') if ocr_result else ''
                
                logger.info(f"Frame {i}: OCR result - {len(ocr_text)} characters detected")
                
                if ocr_text and len(ocr_text) > 50:  # 最小文字数チェック
                    logger.info(f"Frame {i}: Processing OCR text (first 100 chars): {ocr_text[:100]}")
                    
                    # AIを使用して領収書データを抽出
                    receipt_data = None
                    try:
                        # Gemini APIで領収書データ抽出（同期版）
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        try:
                            receipt_data = loop.run_until_complete(
                                analyzer.extract_receipt_data(frame_info['path'], ocr_text)
                            )
                            if receipt_data:
                                logger.info(f"Frame {i}: AI解析成功: vendor={receipt_data.get('vendor')}, total={receipt_data.get('total')}")
                        except Exception as ai_error:
                            logger.warning(f"Frame {i}: AI解析エラー: {ai_error}")
                            import traceback
                            logger.error(f"AI解析エラー詳細: {traceback.format_exc()}")
                    except Exception as e:
                        logger.warning(f"Frame {i}: AI解析失敗: {e}")
                    
                    # フォールバック：パターンマッチング
                    if not receipt_data:
                        try:
                            receipt_data = extract_receipt_info_from_text(ocr_text)
                            if receipt_data:
                                logger.info(f"Frame {i}: パターンマッチング成功")
                        except Exception as pm_error:
                            logger.warning(f"Frame {i}: パターンマッチングエラー: {pm_error}")
                    
                    if receipt_data and receipt_data.get('vendor'):
                        # Frameオブジェクトを作成
                        # フレームイメージをSupabaseにアップロード
                        db_frame_path = frame_info['path']
                        cloud_frame_url = None
                        
                        if use_cloud_storage and storage_service:
                            try:
                                # フレームファイルを読み込み
                                with open(frame_info['path'], 'rb') as f:
                                    frame_content = f.read()
                                
                                # ファイルパス生成
                                frame_filename = os.path.basename(frame_info['path'])
                                cloud_frame_path = storage_service.generate_file_path(0, frame_filename, "frame")
                                
                                # アップロード
                                success, result = storage_service.upload_file_sync(
                                    frame_content,
                                    cloud_frame_path,
                                    "image/jpeg"
                                )
                                
                                if success:
                                    cloud_frame_url = result
                                    db_frame_path = cloud_frame_url
                                    logger.info(f"Frame uploaded to cloud: {cloud_frame_url}")
                                else:
                                    logger.warning(f"Frame cloud upload failed: {result}")
                            except Exception as e:
                                logger.error(f"Frame cloud upload error: {e}")
                        
                        # Render環境での経路調整（クラウド保存失敗時）
                        if not cloud_frame_url and os.getenv("RENDER") == "true":
                            db_frame_path = db_frame_path.replace("/tmp/", "uploads/")
                        
                        try:
                            logger.info(f"Frameオブジェクト作成中: video_id={video_id}, time_ms={frame_info['time_ms']}")
                            frame_obj = Frame(
                                video_id=video_id,
                                time_ms=frame_info['time_ms'],
                                frame_path=db_frame_path,
                                ocr_text=ocr_text,
                                frame_score=frame_info.get('quality_score', 0),  # 品質スコアを保存
                                sharpness=frame_info.get('sharpness', 0),
                                brightness=frame_info.get('brightness', 0),
                                contrast=frame_info.get('contrast', 0),
                                is_best=True
                            )
                            db.add(frame_obj)
                            db.flush()  # IDを取得
                            logger.info(f"Frameオブジェクト保存成功: frame_id={frame_obj.id}")
                        except Exception as frame_error:
                            logger.error(f"Frame保存エラー: {frame_error}")
                            import traceback
                            logger.error(f"Frame保存エラー詳細: {traceback.format_exc()}")
                            continue
                        
                        # 領収書データ保存
                        from datetime import datetime
                        
                        # 日付処理
                        issue_date = receipt_data.get('issue_date')
                        if issue_date and isinstance(issue_date, str):
                            try:
                                issue_date = datetime.strptime(issue_date, '%Y-%m-%d')
                            except:
                                issue_date = datetime.now()
                        elif not issue_date:
                            issue_date = datetime.now()
                        
                        # Receipt作成（正しいフィールド名を使用）
                        try:
                            # document_typeの検証
                            doc_type = receipt_data.get('document_type', 'レシート')
                            if doc_type not in ['領収書', '請求書', 'レシート', '見積書', 'その他', '請求書・領収書']:
                                doc_type = 'レシート'
                            
                            # payment_methodの検証
                            payment = receipt_data.get('payment_method', '現金')
                            if payment not in ['現金', 'クレジット', '電子マネー', '不明']:
                                payment = '現金'
                            
                            logger.info(f"Receipt作成中: vendor={receipt_data.get('vendor')}, doc_type={doc_type}, payment={payment}")
                            
                            receipt = Receipt(
                                video_id=video_id,
                                best_frame_id=frame_obj.id,
                                vendor=receipt_data.get('vendor'),
                                vendor_norm=receipt_data.get('vendor', '').lower().replace(' ', ''),
                                document_type=doc_type,
                                issue_date=issue_date,
                                currency=receipt_data.get('currency', 'JPY'),
                                total=receipt_data.get('total', 0),
                                subtotal=receipt_data.get('subtotal', 0),
                                tax=receipt_data.get('tax', 0),
                                tax_rate=receipt_data.get('tax_rate', 0.1),
                                payment_method=payment,
                                is_manual=False
                            )
                            db.add(receipt)
                            db.commit()
                            logger.info(f"Receipt保存成功: receipt_id={receipt.id}")
                        except Exception as receipt_error:
                            logger.error(f"Receipt保存エラー: {receipt_error}")
                            import traceback
                            logger.error(f"Receipt保存エラー詳細: {traceback.format_exc()}")
                            db.rollback()
                            continue
                        
                        receipts_found += 1
                        logger.info(f"Receipt found: {receipt.vendor} - ¥{receipt.total}")
                        
                        # 仕訳データ生成
                        try:
                            logger.info(f"仕訳データ生成中: receipt_id={receipt.id}")
                            generator = JournalGenerator(db)
                            journal_entries = generator.generate_journal_entries(receipt)
                            for entry_data in journal_entries:
                                journal_entry = JournalEntry(
                                    receipt_id=entry_data.receipt_id,
                                    video_id=entry_data.video_id,
                                    time_ms=frame_info['time_ms'],
                                    debit_account=entry_data.debit_account,
                                    credit_account=entry_data.credit_account,
                                    debit_amount=entry_data.debit_amount,
                                    credit_amount=entry_data.credit_amount,
                                    tax_account=entry_data.tax_account,
                                    tax_amount=entry_data.tax_amount,
                                    memo=entry_data.memo,
                                    status='unconfirmed'
                                )
                                db.add(journal_entry)
                            db.commit()
                            logger.info(f"仕訳データ保存成功")
                        except Exception as journal_error:
                            logger.error(f"仕訳生成エラー: {journal_error}")
                            import traceback
                            logger.error(f"仕訳生成エラー詳細: {traceback.format_exc()}")
                            db.rollback()
                
            except Exception as e:
                logger.error(f"Frame {i} processing error: {e}")
                # エラーが発生しても処理を続行
                try:
                    video.progress = 40 + int(50 * (i + 1) / len(extracted_frames))
                    video.progress_message = f"フレーム {i+1}/{len(extracted_frames)} 処理中..."
                    db.commit()
                except:
                    pass  # DBエラーも無視して続行
                continue
        
        # 完了
        video.status = "done"
        video.progress = 100
        video.progress_message = f"処理完了: {receipts_found}件の領収書を検出"
        db.commit()
        
        logger.info(f"Video {video_id} processing complete: {receipts_found} receipts found")
        
    except Exception as e:
        logger.error(f"Video OCR processing error: {e}", exc_info=True)
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = "error"
            video.progress_message = str(e)[:500]  # エラーメッセージを制限
            video.error_message = str(e)[:500]
            try:
                db.commit()
            except:
                db.rollback()