"""
一時的なユーザー作成API（プロダクション用）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User
from passlib.context import CryptContext
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class CreateUserRequest(BaseModel):
    email: str
    username: str
    password: str

@router.post("/api/temp/create-user")
async def create_temp_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db)
):
    """
    プロダクション環境用の一時的なユーザー作成
    """
    try:
        # 既存ユーザーチェック
        existing = db.query(User).filter(
            (User.email == request.email) | (User.username == request.username)
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": f"ユーザー既存: {existing.email}"
            }
        
        # 新規ユーザー作成
        user = User(
            email=request.email,
            username=request.username,
            hashed_password=pwd_context.hash(request.password),
            full_name=request.username,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        
        logger.info(f"新規ユーザー作成: {request.email}")
        
        return {
            "success": True,
            "message": f"ユーザー作成成功: {request.email}",
            "user": {
                "email": user.email,
                "username": user.username
            }
        }
        
    except Exception as e:
        logger.error(f"ユーザー作成エラー: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/temp/list-users")
async def list_users(db: Session = Depends(get_db)):
    """
    登録済みユーザー一覧
    """
    try:
        from sqlalchemy import text
        # Raw SQLでreset_token情報も取得
        result = db.execute(text("""
            SELECT id, email, username, is_active, 
                   reset_token IS NOT NULL as has_token,
                   reset_token_expires,
                   CASE 
                     WHEN reset_token IS NOT NULL THEN SUBSTRING(reset_token, 1, 10) || '...'
                     ELSE NULL
                   END as token_preview
            FROM users
            ORDER BY id
        """)).fetchall()
        
        return {
            "users": [
                {
                    "id": row.id,
                    "email": row.email,
                    "username": row.username,
                    "is_active": row.is_active,
                    "has_token": row.has_token,
                    "token_expires": str(row.reset_token_expires) if row.reset_token_expires else None,
                    "token_preview": row.token_preview
                }
                for row in result
            ],
            "total": len(result)
        }
    except Exception as e:
        logger.error(f"ユーザー一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/temp/check-user-schema")
async def check_user_schema(db: Session = Depends(get_db)):
    """
    Userテーブルのスキーマを確認
    """
    try:
        from sqlalchemy import inspect
        from models import User
        
        # テーブルのカラム情報を取得
        inspector = inspect(db.bind)
        columns = inspector.get_columns('users')
        
        column_info = {col['name']: str(col['type']) for col in columns}
        
        # reset_token関連のカラムを確認
        has_reset_token = 'reset_token' in column_info
        has_reset_token_expires = 'reset_token_expires' in column_info
        
        return {
            "table": "users",
            "columns": column_info,
            "has_reset_token": has_reset_token,
            "has_reset_token_expires": has_reset_token_expires,
            "total_columns": len(column_info)
        }
    except Exception as e:
        logger.error(f"スキーマ確認エラー: {e}")
        return {"error": str(e)}

@router.get("/api/temp/create-tables")
async def create_tables():
    """
    データベーステーブルを強制作成
    """
    try:
        from database import engine, Base
        from models import User  # Userモデルのみインポート
        
        # テーブル作成
        Base.metadata.create_all(bind=engine, checkfirst=True)
        
        return {
            "success": True,
            "message": "テーブル作成完了",
            "tables": [table.name for table in Base.metadata.sorted_tables]
        }
    except Exception as e:
        logger.error(f"テーブル作成エラー: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@router.get("/api/temp/migrate-reset-columns")
async def migrate_reset_columns():
    """
    reset_token関連カラムを追加するマイグレーション
    """
    try:
        from database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # PostgreSQL用
            if "postgresql" in str(engine.url) or "postgres" in str(engine.url):
                logger.info("PostgreSQL: reset_tokenカラムを追加中...")
                try:
                    # reset_tokenカラムを追加
                    conn.execute(text("""
                        ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)
                    """))
                    conn.commit()
                    logger.info("reset_tokenカラム追加完了")
                except Exception as e:
                    logger.info(f"reset_tokenカラム追加スキップ: {e}")
                
                try:
                    # reset_token_expiresカラムを追加
                    conn.execute(text("""
                        ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP WITH TIME ZONE
                    """))
                    conn.commit()
                    logger.info("reset_token_expiresカラム追加完了")
                except Exception as e:
                    logger.info(f"reset_token_expiresカラム追加スキップ: {e}")
            # SQLite用
            else:
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)"))
                    conn.commit()
                except:
                    pass
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires DATETIME"))
                    conn.commit()
                except:
                    pass
        
        # 現在のスキーマを確認
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = inspector.get_columns('users')
        column_names = [col['name'] for col in columns]
        
        return {
            "success": True,
            "message": "マイグレーション完了",
            "columns": column_names,
            "has_reset_token": 'reset_token' in column_names,
            "has_reset_token_expires": 'reset_token_expires' in column_names
        }
    except Exception as e:
        logger.error(f"マイグレーションエラー: {e}")
        return {
            "success": False,
            "message": str(e)
        }