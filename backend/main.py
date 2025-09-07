from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import engine, Base, get_db
from routers import videos, journals, masters, auth, export, data_sync, password_reset, video_stream
from routers import auth_v2  # 新しい認証ルーター追加
from routers import temp_user  # 一時的なユーザー作成API
from routers import test_email  # メール送信テストAPI
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ポート設定のログ出力
port = int(os.getenv("PORT", 10000))
logger.info(f"サーバーポート設定: {port}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # テーブル作成（既存の場合はスキップ）
        logger.info("データベーステーブルを確認中...")
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("データベース初期化完了")
        
        # マイグレーション実行（新しいカラムを追加）
        try:
            from migrate_db import add_reset_token_columns
            add_reset_token_columns()
            logger.info("マイグレーション完了")
        except Exception as e:
            logger.warning(f"マイグレーションスキップ: {e}")
        
        # 初回起動時のadminユーザー作成
        from sqlalchemy.orm import Session
        from models import User  # Userモデルをインポート
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
        session = Session(engine)
        
        try:
            admin = session.query(User).filter_by(username='admin').first()
            if not admin:
                logger.info("Creating default admin user...")
                admin = User(
                    email='admin@example.com',
                    username='admin',
                    hashed_password=pwd_context.hash('admin123'),
                    full_name='Administrator',
                    is_superuser=True,
                    is_active=True
                )
                session.add(admin)
                session.commit()
                logger.info("✅ Admin user created (username: admin, password: admin123)")
            else:
                logger.info("Admin user already exists")
        finally:
            session.close()
            
    except Exception as e:
        logger.warning(f"データベース初期化警告: {e}")
        # エラーが発生してもアプリケーションは続行
        pass
    
    # Create uploads directory - Render環境では/tmpを使用
    base_dir = "/tmp" if os.getenv("RENDER") == "true" else "uploads"
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(f"{base_dir}/frames", exist_ok=True)
    os.makedirs(f"{base_dir}/videos", exist_ok=True)
    os.makedirs(f"{base_dir}/thumbnails", exist_ok=True)
    
    yield
    # Shutdown
    logger.info("アプリケーションをシャットダウンしています")

app = FastAPI(
    title="動画会計アプリ API",
    description="領収書動画から自動仕訳を生成するシステム",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定 - 開発中は全オリジンを許可
# 本番環境では特定のドメインのみ許可すること
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのオリジンを許可（開発用）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 静的ファイル - Render環境では/tmpを使用
import os
static_dir = "/tmp" if os.getenv("RENDER") == "true" else "uploads"
os.makedirs(static_dir, exist_ok=True)
os.makedirs(f"{static_dir}/frames", exist_ok=True)
os.makedirs(f"{static_dir}/videos", exist_ok=True)
os.makedirs(f"{static_dir}/thumbnails", exist_ok=True)
app.mount("/uploads", StaticFiles(directory=static_dir), name="uploads")

# ルーター登録
app.include_router(auth.router, prefix="/auth", tags=["認証"])
app.include_router(auth_v2.router, prefix="/api/auth", tags=["認証v2"])  # 新しい認証エンドポイント
app.include_router(password_reset.router, tags=["パスワードリセット"])  # パスワードリセットAPI
app.include_router(videos.router, prefix="/videos", tags=["動画"])
app.include_router(journals.router, prefix="/journals", tags=["仕訳"])
app.include_router(masters.router, prefix="/masters", tags=["マスタ"])
app.include_router(export.router, prefix="/export", tags=["エクスポート"])
app.include_router(data_sync.router, tags=["データ同期"])  # データ同期API
app.include_router(video_stream.router, prefix="/videos", tags=["ビデオストリーミング"])  # ビデオストリーミングAPI
app.include_router(temp_user.router, tags=["一時API"])  # 一時的なユーザー作成API
app.include_router(test_email.router, tags=["テスト"])  # メール送信テストAPI

@app.get("/")
async def root():
    return {"message": "動画会計アプリ API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/db-info")
async def database_info(db: Session = Depends(get_db)):
    """データベース情報を取得（デバッグ用）"""
    import os
    from sqlalchemy import text
    
    db_type = "unknown"
    db_info = {}
    
    # DATABASE_URL環境変数の状態
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        if "sqlite" in database_url:
            db_type = "SQLite"
            db_info["path"] = database_url.split("///")[-1] if "///" in database_url else "memory"
        elif "postgresql" in database_url or "postgres" in database_url:
            db_type = "PostgreSQL"
            # URLからホスト名だけ抽出（パスワードは隠す）
            if "@" in database_url:
                db_info["host"] = database_url.split("@")[1].split("/")[0]
            if "supabase" in database_url:
                db_info["provider"] = "Supabase"
    else:
        db_type = "SQLite (fallback)"
        db_info["path"] = "./video_accounting.db"
    
    # データベースの統計情報
    try:
        from models import User, Video, Receipt
        stats = {
            "users": db.query(User).count(),
            "videos": db.query(Video).count(),
            "receipts": db.query(Receipt).count()
        }
        
        # SQLiteの場合、ファイルサイズも確認
        if db_type.startswith("SQLite"):
            import os
            db_path = db_info.get("path", "./video_accounting.db")
            if os.path.exists(db_path):
                db_info["size_mb"] = round(os.path.getsize(db_path) / 1024 / 1024, 2)
                db_info["exists"] = True
            else:
                db_info["exists"] = False
    except Exception as e:
        stats = {"error": str(e)}
    
    return {
        "database_type": db_type,
        "database_info": db_info,
        "render_env": os.getenv("RENDER") == "true",
        "use_sqlite": os.getenv("USE_SQLITE", "false"),
        "statistics": stats
    }

@app.options("/videos/")
async def video_upload_options():
    """CORS preflight用"""
    return {"status": "ok"}

# Render環境用のポート設定
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)