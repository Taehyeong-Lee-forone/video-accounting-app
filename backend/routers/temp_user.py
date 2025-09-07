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
        users = db.query(User).all()
        return {
            "users": [
                {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_active": user.is_active
                }
                for user in users
            ],
            "total": len(users)
        }
    except Exception as e:
        logger.error(f"ユーザー一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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