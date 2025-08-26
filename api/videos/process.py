"""
ビデオ処理API - OCR実行
Vercel Cron Jobまたは手動トリガー用
"""
from typing import Any, Dict
import json
import os
import sys
import base64
import tempfile
from datetime import datetime

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from _utils.database import get_db, engine
from _utils.models import Video, Receipt, Frame, Base
from _utils.storage import get_supabase

# Google Vision API設定
def init_vision_client():
    """Vision APIクライアント初期化"""
    from google.cloud import vision
    from google.oauth2 import service_account
    
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if credentials_json:
        credentials_data = json.loads(base64.b64decode(credentials_json))
        credentials = service_account.Credentials.from_service_account_info(
            credentials_data,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        return vision.ImageAnnotatorClient(credentials=credentials)
    else:
        return vision.ImageAnnotatorClient()

def process_single_frame(image_url: str) -> Dict:
    """
    単一フレームのOCR処理
    """
    client = init_vision_client()
    
    # URLから画像を取得
    from google.cloud import vision
    image = vision.Image()
    image.source.image_uri = image_url
    
    # OCR実行
    response = client.document_text_detection(
        image=image,
        image_context={
            'language_hints': ['ja', 'en'],
            'text_detection_params': {
                'enable_text_detection_confidence_score': True
            }
        }
    )
    
    if response.error.message:
        raise Exception(f"Vision API error: {response.error.message}")
    
    # テキスト抽出
    text = response.full_text_annotation.text if response.full_text_annotation else ""
    
    # 領収書データパース
    receipt_data = parse_receipt_text(text)
    
    return {
        "text": text,
        "receipt_data": receipt_data
    }

def parse_receipt_text(text: str) -> Dict:
    """領収書テキストをパース"""
    import re
    
    # 基本パターン
    patterns = {
        'total': [
            r'合計[：\s]*¥?[\d,]+',
            r'税込[：\s]*¥?[\d,]+',
            r'お支払[：\s]*¥?[\d,]+',
            r'¥[\d,]+',
        ],
        'vendor': [
            r'^[^\d\n]{2,30}$',  # 最初の行の店名
        ],
        'date': [
            r'\d{4}[年/-]\d{1,2}[月/-]\d{1,2}[日]?',
            r'\d{2}[年/-]\d{1,2}[月/-]\d{1,2}[日]?',
        ]
    }
    
    result = {
        "vendor": None,
        "total": None,
        "date": None,
        "raw_text": text
    }
    
    lines = text.split('\n')
    
    # 店名（最初の非空白行）
    for line in lines[:3]:
        if line.strip() and not re.match(r'^\d', line):
            result["vendor"] = line.strip()
            break
    
    # 合計金額
    for pattern in patterns['total']:
        match = re.search(pattern, text)
        if match:
            amount_str = re.sub(r'[^\d]', '', match.group())
            if amount_str:
                result["total"] = float(amount_str)
                break
    
    # 日付
    for pattern in patterns['date']:
        match = re.search(pattern, text)
        if match:
            result["date"] = match.group()
            break
    
    return result

def handler(request: Any) -> Dict:
    """
    POST /api/videos/process
    ビデオからOCR処理を実行
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
        video_id = body.get('video_id')
        
        if not video_id:
            # 未処理のビデオを自動選択（Cron Job用）
            Base.metadata.create_all(bind=engine)
            db = next(get_db())
            video = db.query(Video).filter(Video.status == "queued").first()
            if not video:
                db.close()
                return {
                    "statusCode": 200,
                    "body": json.dumps({"message": "No videos to process"})
                }
            video_id = video.id
        else:
            # 指定されたビデオを取得
            Base.metadata.create_all(bind=engine)
            db = next(get_db())
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                db.close()
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Video not found"})
                }
        
        # ステータス更新
        video.status = "processing"
        video.progress = 10
        video.progress_message = "OCR処理を開始"
        db.commit()
        
        # Supabaseから画像URLを取得（ビデオから抽出された代表フレーム）
        # 注：実際のビデオ処理は別のサービスで行う必要があります
        # ここではシンプルに最初のフレームのみ処理
        
        # OCR処理実行
        if video.gcs_uri:  # Supabase URL
            ocr_result = process_single_frame(video.gcs_uri)
            
            # 領収書データ保存
            receipt = Receipt(
                video_id=video.id,
                vendor=ocr_result["receipt_data"].get("vendor"),
                total=ocr_result["receipt_data"].get("total"),
                ocr_raw_text=ocr_result["text"],
                document_type="領収書",
                status="unconfirmed"
            )
            db.add(receipt)
            
            # ステータス更新
            video.status = "done"
            video.progress = 100
            video.progress_message = "処理完了"
            db.commit()
            
            result = {
                "video_id": video.id,
                "status": "success",
                "receipt": {
                    "vendor": receipt.vendor,
                    "total": receipt.total
                }
            }
        else:
            video.status = "error"
            video.error_message = "ビデオURLが見つかりません"
            db.commit()
            result = {"video_id": video.id, "status": "error"}
        
        db.close()
        
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