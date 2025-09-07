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
        
        # トークンをユーザーレコードに保存（24時間有効）
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now() + timedelta(hours=24)
        db.commit()
        
        logger.info(f"トークン保存完了: token={reset_token[:10]}..., user_id={user.id}, expires_at={user.reset_token_expires}")
        
        # メール送信を試みる
        email_sent = False
        try:
            logger.info(f"メール送信開始: {user.email} (ユーザー: {user.username})")
            
            # 環境変数の確認
            import os
            smtp_user = os.getenv("SMTP_USER", "未設定")
            logger.info(f"SMTP設定確認 - SMTP_USER: {smtp_user}")
            
            email_sent = email_service.send_password_reset_email(
                to_email=user.email,
                reset_token=reset_token,
                username=user.username
            )
            
            if email_sent:
                logger.info(f"メール送信成功: {user.email}")
            else:
                logger.warning(f"メール送信失敗: {user.email}")
                
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
        user = db.query(User).filter(
            User.reset_token == request.token
        ).first()
        
        if not user:
            logger.warning(f"トークンが見つかりません: token={request.token[:10] if request.token else 'None'}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なトークンです"
            )
        
        # 有効期限をチェック
        if not user.reset_token_expires or datetime.now() > user.reset_token_expires:
            # 期限切れトークンをクリア
            user.reset_token = None
            user.reset_token_expires = None
            db.commit()
            logger.warning(f"トークン期限切れ: expires_at={user.reset_token_expires}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="トークンの有効期限が切れています"
            )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ユーザーが見つかりません"
            )
        
        # パスワードを更新
        user.hashed_password = pwd_context.hash(request.new_password)
        
        # トークンをクリア
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        
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
async def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """
    リセットトークンの有効性を確認
    """
    logger.info(f"トークン検証開始: token={token[:10] if token else 'None'}...")
    
    # トークンでユーザーを検索
    user = db.query(User).filter(
        User.reset_token == token
    ).first()
    
    if not user:
        logger.warning(f"トークンが見つかりません: token={token[:10] if token else 'None'}...")
        return {"valid": False, "message": "無効なトークンです"}
    
    if not user.reset_token_expires or datetime.now() > user.reset_token_expires:
        # 期限切れトークンをクリア
        logger.warning(f"トークン期限切れ: expires_at={user.reset_token_expires}, now={datetime.now()}")
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        return {"valid": False, "message": "トークンの有効期限が切れています"}
    
    logger.info(f"トークン有効: user_email={user.email}")
    return {
        "valid": True,
        "email": user.email,
        "message": "有効なトークンです"
    }