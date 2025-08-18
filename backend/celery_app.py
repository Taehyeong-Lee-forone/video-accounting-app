from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Celery設定
celery_app = Celery(
    'video_accounting',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tokyo',
    enable_utc=True,
)

@celery_app.task
def analyze_video_task(video_id: int):
    """動画分析タスク（非同期処理用）"""
    # ここに動画分析処理を実装
    return {"status": "completed", "video_id": video_id}