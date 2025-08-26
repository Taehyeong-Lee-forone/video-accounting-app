"""
ビデオアップロードAPI - Supabase Storage直接アップロード
"""
from typing import Any, Dict
import json
import os
import sys
import base64
from datetime import datetime
import hashlib

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from _utils.database import get_db, engine
from _utils.models import Video, Base
from _utils.storage import get_supabase

def handler(request: Any) -> Dict:
    """
    POST /api/videos/upload
    ビデオファイルをSupabase Storageにアップロード
    """
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }
    
    if request.method != "POST":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "Method not allowed"})
        }
    
    try:
        # リクエストボディ取得
        body = json.loads(request.body) if hasattr(request, 'body') else {}
        
        # Base64エンコードされたファイルデータ
        file_data_base64 = body.get('file_data')
        filename = body.get('filename', 'video.mp4')
        content_type = body.get('content_type', 'video/mp4')
        
        if not file_data_base64:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No file data provided"})
            }
        
        # Base64デコード
        file_data = base64.b64decode(file_data_base64)
        
        # ユニークなファイル名生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_hash = hashlib.md5(file_data[:1024]).hexdigest()[:8]
        unique_filename = f"{timestamp}_{file_hash}_{filename}"
        
        # Supabase Storageにアップロード
        supabase = get_supabase()
        storage_path = f"videos/{unique_filename}"
        
        # アップロード実行
        response = supabase.storage.from_("videos").upload(
            storage_path,
            file_data,
            {"content-type": content_type}
        )
        
        # 公開URL取得
        public_url = supabase.storage.from_("videos").get_public_url(storage_path)
        
        # データベースに記録
        Base.metadata.create_all(bind=engine)
        db = next(get_db())
        
        video = Video(
            filename=filename,
            gcs_uri=public_url,  # Supabase URLを保存
            status="queued",
            progress=0,
            progress_message="アップロード完了、処理待機中"
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        result = {
            "id": video.id,
            "filename": video.filename,
            "url": public_url,
            "status": video.status,
            "created_at": video.created_at.isoformat() if video.created_at else None
        }
        
        db.close()
        
        # 処理開始をトリガー（別のAPIまたはCron Jobで実行）
        # TODO: Vercel Cron または Edge Functionで処理
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": str(e)})
        }