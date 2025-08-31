from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List
import os
import shutil
from pathlib import Path
import logging
import cv2

from database import get_db
from models import Video, Frame, Receipt, JournalEntry, ReceiptHistory
from schemas import VideoResponse, VideoDetailResponse, VideoAnalyzeRequest, FrameResponse, ReceiptUpdate
from services.video_intelligence import VideoAnalyzer
from services.journal_generator import JournalGenerator
from celery_app import analyze_video_task
from video_processing import select_receipt_frames

logger = logging.getLogger(__name__)

router = APIRouter()

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
    db: Session = Depends(get_db)
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
            with file_path.open("wb") as buffer:
                buffer.write(file_content)
            
            logger.info(f"ファイル保存成功: {file_path.exists()}")
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
            cap.release()
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")
            thumbnail_path = None
        
        # DB登録 - 元のファイル名を保持
        video = Video(
            filename=file.filename,  # 元のファイル名を保持
            local_path=str(file_path),  # 実際の保存パス
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            status="processing",  # 自動的に処理開始
            progress=10  # 初期進捗を10に設定
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # VideoResponseに必要な追加フィールドを設定
        video.receipts_count = 0
        video.auto_receipts_count = 0
        video.manual_receipts_count = 0
        
        logger.info(f"ビデオDB登録成功: ID={video.id}")
        
        # 実際のOCR処理を開始
        try:
            # バックグラウンドで処理を開始
            background_tasks.add_task(
                process_video_ocr,
                video.id,
                db
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
            video.progress_message = str(e)
            db.commit()
        
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
            
            # インテリジェントフレーム選択（序盤集中 + 均等分割）
            frames_data = distribute_frames_intelligently(frames_data, target_max)
        
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
                frame_score=frame_data['frame_score'],
                frame_path=frame_data['frame_path']
            )
            
            # OCRテキストをマッピング
            for annotation in ocr_result['text_annotations']:
                for segment in annotation['segments']:
                    if segment['start_time_ms'] <= frame_data['time_ms'] <= segment['end_time_ms']:
                        frame.ocr_text = annotation['text']
                        frame.ocr_boxes_json = str(segment['frames'])
                        break
            
            db.add(frame)
            frames.append(frame)
        
        # スマートフレーム抽出を使用した場合、すべてのフレームが既に最適化されている
        # 通常の抽出の場合のみ、追加のフィルタリングを行う
        logger.info(f"Total frames available: {len(frames)}")
        
        # すべてのフレームを品質スコアでソート
        frames_by_quality = sorted(frames, key=lambda x: x.frame_score or 0, reverse=True)
        
        # スマートフレーム抽出の場合はすべてを使用、そうでない場合は選択
        if len(frames) <= 30:  # スマートフレーム抽出は通常30フレーム以下
            selected_frames = frames  # すべてのフレームを使用
            for frame in selected_frames:
                frame.is_best = True
        else:
            # 通常の抽出の場合、間隔と品質で選択
            selected_frames = []
            last_time = -1500  # 1.5秒間隔
            
            # 間隔ベースの選択
            for frame in sorted(frames, key=lambda x: x.time_ms):
                if frame.time_ms - last_time >= 1500:  # 1.5秒以上離れている
                    selected_frames.append(frame)
                    last_time = frame.time_ms
                    frame.is_best = True
            
            # 高品質フレームも追加（上位20%）
            high_quality_count = max(5, len(frames) // 5)  # 最低5枚、または全体の20%
            for frame in frames_by_quality[:high_quality_count]:
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
                
                # ラインアイテム有効性チェック
                line_items = receipt_data.get('line_items', [])
                valid_line_items = [item for item in line_items if item and item.get('name') and item.get('name') != '不明']
                
                # より緩い条件：金額があり、極端に無効でなければ保存
                if (len(vendor) < 1 or  # 販売店名が空
                    any(invalid in vendor_normalized for invalid in invalid_vendors) or  # 明らかに無効な販売店
                    not total or total <= 0 or  # 金額がないか0円
                    total > 10000000):  # 非現実的に大きい金額（1000万円超）
                    logger.info(f"Skipping low-quality receipt: vendor='{vendor}', total={total}, valid_items={len(valid_line_items)}")
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
async def get_video(video_id: int, db: Session = Depends(get_db)):
    """動画詳細取得"""
    try:
        # receiptsとbest_frame、history関係を一緒にロード
        video = db.query(Video).options(
            joinedload(Video.receipts).joinedload(Receipt.best_frame),
            joinedload(Video.receipts).joinedload(Receipt.history)
        ).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(404, "動画が見つかりません")
        
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
    
    if not os.path.exists(frame.frame_path):
        raise HTTPException(404, "フレーム画像ファイルが見つかりません")
    
    return FileResponse(frame.frame_path, media_type="image/jpeg")

@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """動画一覧取得"""
    try:
        # 最新のビデオが先に来るようにソート
        videos = db.query(Video).order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
        
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
    
    if not os.path.exists(frame.frame_path):
        raise HTTPException(404, "画像ファイルが見つかりません")
    
    return FileResponse(frame.frame_path, media_type="image/jpeg")

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
    
    video_path = video.local_path
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
    
    # サムネイルがなければ生成を試みる
    if not video.thumbnail_path or not os.path.exists(video.thumbnail_path):
        # 動的にサムネイル生成
        if video.local_path and os.path.exists(video.local_path):
            try:
                import cv2
                thumbnail_dir = Path("uploads/thumbnails")
                thumbnail_dir.mkdir(parents=True, exist_ok=True)
                thumbnail_filename = f"{Path(video.local_path).stem}_thumb.jpg"
                thumbnail_path = thumbnail_dir / thumbnail_filename
                
                cap = cv2.VideoCapture(video.local_path)
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
                    
                    # DBアップデート
                    video.thumbnail_path = str(thumbnail_path)
                    db.commit()
                    
                cap.release()
                return FileResponse(str(thumbnail_path), media_type="image/jpeg")
            except Exception as e:
                logger.error(f"Thumbnail generation failed: {e}")
        
        # デフォルト画像を返すか404
        raise HTTPException(404, "サムネイルが見つかりません")
    
    return FileResponse(video.thumbnail_path, media_type="image/jpeg")

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
        
        frame_filename = f"manual_frame_{video_id}_{actual_time_ms}.jpg"
        frame_path = f"uploads/frames/{frame_filename}"
        cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 100])  # 最高品質で保存
        cap.release()
        
        logger.info(f"Frame capture - Requested: {time_ms}ms (frame {target_frame}), Actual: {actual_time_ms}ms (frame {actual_frame}), FPS: {fps}")
        
        # フレーム品質分析（実際の時刻を使用）
        frame_data = analyzer._analyze_frame(frame_path, actual_time_ms)
        
        # フレームをDBに保存（実際の時刻を使用）
        frame_obj = Frame(
            video_id=video_id,
            time_ms=actual_time_ms,  # 実際の時刻を保存
            sharpness=frame_data['sharpness'],
            brightness=frame_data['brightness'],
            contrast=frame_data['contrast'],
            phash=frame_data['phash'],
            frame_score=frame_data['frame_score'],
            frame_path=frame_path,
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
        output_dir = Path("uploads/frames")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import time
        timestamp = int(time.time() * 1000)
        frame_filename = f"{timestamp}_frame_{actual_time_ms:08d}ms.jpg"
        frame_path = str(output_dir / frame_filename)
        cv2.imwrite(frame_path, frame)
        
        # 画像分析（品質スコア、pHash等）
        analyzer = VideoAnalyzer()
        frame_data = analyzer._analyze_frame(frame_path, actual_time_ms)
        
        # 新しいFrameオブジェクトを作成
        new_frame = Frame(
            video_id=video_id,
            time_ms=actual_time_ms,
            frame_path=frame_path,
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
    """ビデオ削除"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    # 関連データも一緒に削除（CASCADE設定がない場合）
    db.query(Frame).filter(Frame.video_id == video_id).delete()
    db.query(Receipt).filter(Receipt.video_id == video_id).delete()
    db.query(JournalEntry).filter(JournalEntry.video_id == video_id).delete()
    
    # ローカルファイル削除
    if video.local_path and os.path.exists(video.local_path):
        try:
            os.remove(video.local_path)
        except:
            pass
    
    # ビデオレコード削除
    db.delete(video)
    db.commit()
    
    return {"message": "動画を削除しました"}

async def process_video_ocr(video_id: int, db: Session):
    """
    実際のOCR処理を実行
    Google Vision APIを使用して領収書を検出・認識
    """
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
        
        # 必要なディレクトリを作成（絶対パスを使用）
        import os
        base_path = Path(os.path.dirname(os.path.abspath(__file__))).parent  # backend/
        frames_dir = base_path / "uploads" / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        # Vision OCRサービスを使用
        from services.vision_ocr import VisionOCRService
        ocr_service = VisionOCRService()
        
        # VideoAnalyzerインスタンス作成（領収書データ抽出用）
        analyzer = VideoAnalyzer()
        
        # 動画からフレーム抽出（2秒間隔）
        cap = cv2.VideoCapture(video.local_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Video info: {duration_sec:.1f}秒, {total_frames}フレーム, {fps:.1f}fps")
        
        # 2秒ごとにフレーム抽出（処理時間を考慮）
        extracted_frames = []
        interval_sec = 2  # 2秒間隔
        for sec in range(0, int(duration_sec) + 1, interval_sec):
            frame_number = int(sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret:
                # フレーム保存（絶対パスを使用）
                frame_filename = f"frame_{video_id}_{sec:04d}.jpg"
                frame_path = str(frames_dir / frame_filename)
                cv2.imwrite(frame_path, frame)
                extracted_frames.append({
                    'path': frame_path,
                    'time_ms': sec * 1000
                })
        
        cap.release()
        logger.info(f"Extracted {len(extracted_frames)} frames")
        
        # 進行状況更新
        video.progress = 40
        video.progress_message = f"{len(extracted_frames)}枚のフレームをOCR処理中..."
        db.commit()
        
        # 各フレームをOCR処理
        receipts_found = 0
        for i, frame_info in enumerate(extracted_frames):
            try:
                # 進行状況更新
                progress = 40 + int(40 * i / len(extracted_frames))
                video.progress = progress
                video.progress_message = f"フレーム {i+1}/{len(extracted_frames)} 分析中..."
                db.commit()
                
                # Vision APIでOCR実行
                ocr_result = ocr_service.extract_text_from_image(frame_info['path'])
                ocr_text = ocr_result.get('full_text', '') if ocr_result else ''
                
                logger.info(f"Frame {i}: OCR result - {len(ocr_text)} characters detected")
                
                if ocr_text and len(ocr_text) > 50:  # 最小文字数チェック
                    logger.info(f"Frame {i}: Processing OCR text (first 100 chars): {ocr_text[:100]}")
                    
                    # Gemini APIで領収書データ抽出
                    receipt_data = await analyzer.extract_receipt_data(frame_info['path'], ocr_text)
                    logger.info(f"Frame {i}: Receipt data extraction result: {bool(receipt_data)}")
                    
                    if receipt_data and receipt_data.get('vendor'):
                        # Frameオブジェクトを作成
                        frame_obj = Frame(
                            video_id=video_id,
                            time_ms=frame_info['time_ms'],
                            frame_path=frame_info['path'],
                            ocr_text=ocr_text,
                            is_best=True
                        )
                        db.add(frame_obj)
                        db.flush()  # IDを取得
                        
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
                        receipt = Receipt(
                            video_id=video_id,
                            best_frame_id=frame_obj.id,
                            vendor=receipt_data.get('vendor'),
                            vendor_norm=analyzer._normalize_text(receipt_data.get('vendor', '')),
                            document_type=receipt_data.get('document_type', 'レシート'),
                            issue_date=issue_date,
                            currency=receipt_data.get('currency', 'JPY'),
                            total=receipt_data.get('total', 0),
                            subtotal=receipt_data.get('subtotal', 0),
                            tax=receipt_data.get('tax', 0),
                            tax_rate=receipt_data.get('tax_rate', 0.1),
                            payment_method=receipt_data.get('payment_method', '現金'),
                            is_manual=False
                        )
                        db.add(receipt)
                        db.commit()
                        
                        receipts_found += 1
                        logger.info(f"Receipt found: {receipt.vendor} - ¥{receipt.total}")
                        
                        # 仕訳データ生成
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
                
            except Exception as e:
                logger.error(f"Frame {i} processing error: {e}", exc_info=True)
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
            video.progress_message = str(e)
            db.commit()