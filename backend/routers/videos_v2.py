"""
改善されたビデオルーター（クラウドストレージ統合）
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import logging
from pathlib import Path

from database import get_db
from models import Video
from models_user import User
from services.storage import StorageService
from services.auth_service import get_current_user
from schemas import VideoResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# ストレージサービス初期化
storage_service = StorageService()

@router.post("/", response_model=VideoResponse)
async def upload_video_v2(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 認証必須
):
    """
    改善された動画アップロード
    - ユーザー認証必須
    - クラウドストレージに保存
    - ユーザーごとのストレージ容量チェック
    """
    try:
        # 1. ファイル検証
        if not file.filename:
            raise HTTPException(400, "ファイル名が空です")
        
        if not file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.webm', '.mkv')):
            raise HTTPException(400, "サポートされていないファイル形式です")
        
        # 2. ファイルサイズチェック
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        
        if file_size_mb > 100:  # 100MB制限
            raise HTTPException(400, f"ファイルサイズが大きすぎます: {file_size_mb:.1f}MB (最大100MB)")
        
        # 3. ユーザーのストレージ容量チェック
        if not current_user.has_storage_space(file_size_mb):
            used_gb = current_user.storage_used_mb / 1024
            quota_gb = current_user.storage_quota_mb / 1024
            raise HTTPException(
                400, 
                f"ストレージ容量が不足しています。使用中: {used_gb:.1f}GB / {quota_gb:.1f}GB"
            )
        
        logger.info(f"User {current_user.username} uploading {file.filename} ({file_size_mb:.1f}MB)")
        
        # 4. クラウドストレージにアップロード
        file_path = storage_service.generate_file_path(
            user_id=current_user.id,
            filename=file.filename,
            file_type="video"
        )
        
        success, url_or_error = await storage_service.upload_file(
            file_content=file_content,
            file_path=file_path,
            content_type=file.content_type
        )
        
        if not success:
            logger.error(f"Cloud storage upload failed: {url_or_error}")
            raise HTTPException(500, f"アップロードに失敗しました: {url_or_error}")
        
        cloud_url = url_or_error
        logger.info(f"Uploaded to cloud: {cloud_url}")
        
        # 5. 一時的にローカルにも保存（処理用）
        temp_dir = Path("/tmp") if os.getenv("RENDER") == "true" else Path("temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        import uuid
        temp_filename = f"{uuid.uuid4()}.mp4"
        temp_path = temp_dir / temp_filename
        
        with open(temp_path, "wb") as f:
            f.write(file_content)
        
        # 6. データベースに記録
        video = Video(
            filename=file.filename,
            user_id=current_user.id,  # ユーザーID設定
            cloud_url=cloud_url,       # クラウドURL保存
            local_path=str(temp_path), # 一時パス（処理用）
            file_size_mb=file_size_mb,
            status="queued",
            progress=0
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # 7. ユーザーのストレージ使用量更新
        current_user.storage_used_mb += file_size_mb
        db.commit()
        
        # 8. バックグラウンドで処理開始
        if background_tasks:
            background_tasks.add_task(
                process_video_async,
                video_id=video.id,
                temp_path=str(temp_path),
                db=db
            )
        
        # 9. レスポンス用の追加フィールド設定
        video.receipts_count = 0
        video.auto_receipts_count = 0
        video.manual_receipts_count = 0
        
        logger.info(f"Video {video.id} uploaded successfully by user {current_user.username}")
        
        return video
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(500, f"アップロードに失敗しました: {str(e)}")


@router.get("/", response_model=List[VideoResponse])
async def list_user_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 認証必須
):
    """
    現在のユーザーの動画一覧取得
    """
    try:
        # ユーザーの動画のみ取得
        videos = db.query(Video).filter(
            Video.user_id == current_user.id  # ユーザーでフィルタ
        ).order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
        
        # レシート数を追加
        for video in videos:
            from models import Receipt
            receipts = db.query(Receipt).filter(
                Receipt.video_id == video.id,
                Receipt.user_id == current_user.id  # ユーザーでフィルタ
            ).all()
            
            video.receipts_count = len(receipts)
            video.auto_receipts_count = len([r for r in receipts if not r.is_manual])
            video.manual_receipts_count = len([r for r in receipts if r.is_manual])
        
        return videos
        
    except Exception as e:
        logger.error(f"List videos error: {e}", exc_info=True)
        return []


@router.get("/{video_id}", response_model=VideoResponse)
async def get_user_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    特定の動画詳細取得（所有者のみ）
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id  # 所有者チェック
    ).first()
    
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    return video


@router.delete("/{video_id}")
async def delete_user_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    動画削除（所有者のみ）
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id  # 所有者チェック
    ).first()
    
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    try:
        # クラウドストレージからも削除
        if video.cloud_url:
            # URLからファイルパスを抽出
            file_path = extract_file_path_from_url(video.cloud_url)
            await storage_service.delete_file(file_path)
        
        # ストレージ使用量を減らす
        if video.file_size_mb:
            current_user.storage_used_mb -= video.file_size_mb
            if current_user.storage_used_mb < 0:
                current_user.storage_used_mb = 0
        
        # データベースから削除
        db.delete(video)
        db.commit()
        
        return {"message": "動画を削除しました"}
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(500, f"削除に失敗しました: {str(e)}")


async def process_video_async(video_id: int, temp_path: str, db: Session):
    """
    バックグラウンドで動画処理
    処理後、一時ファイルを削除
    """
    try:
        # ここで動画分析処理を実行
        # ...
        
        # 処理完了後、一時ファイルを削除
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info(f"Deleted temp file: {temp_path}")
            
    except Exception as e:
        logger.error(f"Background processing error: {e}")


def extract_file_path_from_url(url: str) -> str:
    """URLからファイルパスを抽出"""
    # 実装はストレージタイプによって異なる
    # 例: https://xxx.supabase.co/storage/v1/object/public/videos/users/1/videos/2024/01/abc_test.mp4
    # → users/1/videos/2024/01/abc_test.mp4
    
    if "supabase" in url:
        parts = url.split("/public/")[-1]
        return parts
    elif "s3.amazonaws.com" in url:
        parts = url.split(".com/")[-1]
        return parts
    elif "storage.googleapis.com" in url:
        parts = url.split(".com/")[-1].split("/", 1)[-1]
        return parts
    
    return ""