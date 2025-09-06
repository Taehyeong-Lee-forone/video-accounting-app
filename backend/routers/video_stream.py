from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_video_path(filename: str) -> Path:
    """ビデオファイルのパスを取得"""
    # Render環境では/tmpを使用
    base_dir = "/tmp" if os.getenv("RENDER") == "true" else "uploads"
    video_path = Path(base_dir) / "videos" / filename
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return video_path

def range_requests_response(
    request: Request,
    file_path: Path,
    content_type: str = "video/mp4"
) -> Response:
    """Range要求に対応したビデオストリーミングレスポンスを生成"""
    
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")
    
    # Range要求がない場合は通常のレスポンス
    if not range_header:
        def iterfile():
            with open(file_path, "rb") as f:
                yield from f
        
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            }
        )
    
    # Range要求の解析
    range_start = 0
    range_end = file_size - 1
    
    try:
        range_spec = range_header.replace("bytes=", "")
        range_parts = range_spec.split("-")
        
        if range_parts[0]:
            range_start = int(range_parts[0])
        if range_parts[1]:
            range_end = int(range_parts[1])
            
    except (ValueError, IndexError):
        # 不正なRange要求の場合は通常のレスポンス
        def iterfile():
            with open(file_path, "rb") as f:
                yield from f
        
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            }
        )
    
    # 範囲の検証
    range_start = max(0, min(range_start, file_size - 1))
    range_end = max(range_start, min(range_end, file_size - 1))
    content_length = range_end - range_start + 1
    
    # 部分コンテンツの生成
    def iterfile():
        with open(file_path, "rb") as f:
            f.seek(range_start)
            remaining = content_length
            chunk_size = 8192  # 8KB chunks
            
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data
    
    # 206 Partial Content レスポンス
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Range": f"bytes {range_start}-{range_end}/{file_size}",
        "Content-Type": content_type,
    }
    
    return StreamingResponse(
        iterfile(),
        status_code=206,
        headers=headers,
        media_type=content_type
    )

@router.get("/stream/{filename}")
async def stream_video(filename: str, request: Request):
    """
    ビデオファイルをストリーミング配信
    Range要求に対応し、シーク可能な再生を実現
    """
    try:
        video_path = get_video_path(filename)
        
        # ファイル拡張子からMIMEタイプを判定
        content_type = "video/mp4"  # デフォルト
        if filename.lower().endswith(".mov"):
            content_type = "video/quicktime"
        elif filename.lower().endswith(".avi"):
            content_type = "video/x-msvideo"
        elif filename.lower().endswith(".webm"):
            content_type = "video/webm"
        
        logger.info(f"Streaming video: {filename}, Range: {request.headers.get('range', 'none')}")
        
        return range_requests_response(request, video_path, content_type)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming video {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))