"""
ビデオ一覧取得API
"""
from typing import Any, Dict
import json
import os
import sys
from datetime import datetime

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from _utils.database import get_db, engine
from _utils.models import Video, Receipt, Base
from sqlalchemy import desc

def handler(request: Any) -> Dict:
    """
    GET /api/videos/list
    ビデオ一覧を取得
    """
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }
    
    if request.method != "GET":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "Method not allowed"})
        }
    
    try:
        # データベース接続
        Base.metadata.create_all(bind=engine)
        db = next(get_db())
        
        # クエリパラメータ取得
        query_params = request.args if hasattr(request, 'args') else {}
        limit = int(query_params.get('limit', 20))
        offset = int(query_params.get('offset', 0))
        
        # ビデオ一覧取得
        videos = db.query(Video)\
            .order_by(desc(Video.created_at))\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        # レシートデータも取得
        video_ids = [v.id for v in videos]
        receipts = db.query(Receipt).filter(Receipt.video_id.in_(video_ids)).all()
        receipt_map = {r.video_id: r for r in receipts}
        
        # レスポンス作成
        result = []
        for video in videos:
            receipt = receipt_map.get(video.id)
            result.append({
                "id": video.id,
                "filename": video.filename,
                "status": video.status,
                "progress": video.progress,
                "progress_message": video.progress_message,
                "duration_ms": video.duration_ms,
                "created_at": video.created_at.isoformat() if video.created_at else None,
                "receipt": {
                    "id": receipt.id,
                    "vendor": receipt.vendor,
                    "total": receipt.total,
                    "issue_date": receipt.issue_date.isoformat() if receipt.issue_date else None,
                    "document_type": receipt.document_type
                } if receipt else None
            })
        
        db.close()
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "videos": result,
                "total": len(result),
                "offset": offset,
                "limit": limit
            }, ensure_ascii=False)
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