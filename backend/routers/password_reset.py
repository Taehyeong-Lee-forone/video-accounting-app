"""
パスワードリセットAPI
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import secrets
import logging
from typing import Optional

from database import get_db
from models import User
from services.email import email_service
from passlib.context import CryptContext

logger = logging.getLogger(__name__)
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# リセットトークンを一時保存（本番環境ではRedisやDBを使用）
reset_tokens = {}

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class PasswordResetResponse(BaseModel):
    message: str
    success: bool

@router.post("/api/auth/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    パスワードリセットメールを送信
    """
    try:
        # ユーザーを検索
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # セキュリティのため、ユーザーが存在しない場合も成功を返す
            logger.warning(f"パスワードリセット要求: 存在しないメール {request.email}")
            return PasswordResetResponse(
                message="メールアドレスが登録されている場合は、パスワードリセットメールを送信しました。",
                success=True
            )
        
        # リセットトークンを生成
        reset_token = secrets.token_urlsafe(32)
        
        # トークンを保存（24時間有効）
        reset_tokens[reset_token] = {
            "user_id": user.id,
            "email": user.email,
            "expires_at": datetime.now() + timedelta(hours=24)
        }
        
        # メール送信を試みる
        email_sent = False
        try:
            email_sent = email_service.send_password_reset_email(
                to_email=user.email,
                reset_token=reset_token,
                username=user.username
            )
        except Exception as e:
            logger.error(f"メール送信エラー: {e}")
        
        if not email_sent:
            # メール送信に失敗した場合でも、開発環境ではトークンをログに出力
            logger.info(f"[開発用] パスワードリセットトークン: {reset_token}")
            logger.info(f"[開発用] リセットURL: https://video-accounting-app.vercel.app/reset-password?token={reset_token}")
            
            # デモモードの場合はトークンを返す（開発環境のみ）
            import os
            if os.getenv("DEMO_MODE") == "true":
                return PasswordResetResponse(
                    message=f"デモモード: リセットトークン {reset_token}",
                    success=True
                )
        
        return PasswordResetResponse(
            message="メールアドレスが登録されている場合は、パスワードリセットメールを送信しました。",
            success=True
        )
        
    except Exception as e:
        logger.error(f"パスワードリセットエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワードリセット処理中にエラーが発生しました"
        )

@router.post("/api/auth/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    新しいパスワードを設定
    """
    try:
        # トークンを検証
        token_data = reset_tokens.get(request.token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なトークンです"
            )
        
        # 有効期限をチェック
        if datetime.now() > token_data["expires_at"]:
            # 期限切れトークンを削除
            del reset_tokens[request.token]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="トークンの有効期限が切れています"
            )
        
        # ユーザーを取得
        user = db.query(User).filter(User.id == token_data["user_id"]).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ユーザーが見つかりません"
            )
        
        # パスワードを更新
        user.hashed_password = pwd_context.hash(request.new_password)
        db.commit()
        
        # 使用済みトークンを削除
        del reset_tokens[request.token]
        
        logger.info(f"パスワードリセット完了: {user.email}")
        
        return PasswordResetResponse(
            message="パスワードが正常に更新されました",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"パスワードリセットエラー: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワード更新中にエラーが発生しました"
        )

@router.get("/api/auth/verify-reset-token")
async def verify_reset_token(token: str):
    """
    リセットトークンの有効性を確認
    """
    token_data = reset_tokens.get(token)
    
    if not token_data:
        return {"valid": False, "message": "無効なトークンです"}
    
    if datetime.now() > token_data["expires_at"]:
        del reset_tokens[token]
        return {"valid": False, "message": "トークンの有効期限が切れています"}
    
    return {
        "valid": True,
        "email": token_data["email"],
        "message": "有効なトークンです"
    }