from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from database import engine, Base
from routers import videos, journals, masters, auth, export
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logger.info("データベーステーブルを作成しました")
    
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("uploads/frames", exist_ok=True)
    os.makedirs("uploads/videos", exist_ok=True)
    
    yield
    # Shutdown
    logger.info("アプリケーションをシャットダウンしています")

app = FastAPI(
    title="動画会計アプリ API",
    description="領収書動画から自動仕訳を生成するシステム",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定 - 環境変数から取得
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins + ["https://*.ngrok-free.app", "https://*.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイル
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ルーター登録
app.include_router(auth.router, prefix="/auth", tags=["認証"])
app.include_router(videos.router, prefix="/videos", tags=["動画"])
app.include_router(journals.router, prefix="/journals", tags=["仕訳"])
app.include_router(masters.router, prefix="/masters", tags=["マスタ"])
app.include_router(export.router, prefix="/export", tags=["エクスポート"])

@app.get("/")
async def root():
    return {"message": "動画会計アプリ API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}