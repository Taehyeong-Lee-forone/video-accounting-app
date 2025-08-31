"""
改善された認証ルーター
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import secrets

from database import get_db
from models import User
from schemas import UserCreate, UserResponse, TokenResponse
from services.auth_service import (
    authenticate_user, 
    create_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """新規ユーザー登録"""
    try:
        # メールアドレス重複チェック
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=400,
                detail="このメールアドレスは既に登録されています"
            )
        
        # ユーザー名重複チェック
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(
                status_code=400,
                detail="このユーザー名は既に使用されています"
            )
        
        # ユーザー作成
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"ユーザー登録に失敗しました: {str(e)}")

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """ログイン（JWT発行）"""
    # ユーザー認証（ユーザー名またはメールアドレス）
    user = await authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="アカウントが無効です"
        )
    
    # 最終ログイン時刻更新
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # トークン生成
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 秒単位
    }

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """現在のユーザー情報取得"""
    return current_user

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """リフレッシュトークンで新しいアクセストークンを取得"""
    try:
        from jose import jwt, JWTError
        from services.auth_service import SECRET_KEY, ALGORITHM
        
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なリフレッシュトークンです"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません"
            )
        
        # 新しいアクセストークン生成
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token,  # リフレッシュトークンは同じものを返す
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なリフレッシュトークンです"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ログアウト"""
    # セッショントークンを無効化する場合はここで処理
    # JWTの場合、クライアント側でトークンを削除するだけでOK
    return {"message": "ログアウトしました"}

@router.put("/me", response_model=UserResponse)
async def update_profile(
    full_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プロフィール更新"""
    try:
        if full_name:
            current_user.full_name = full_name
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        return current_user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"プロフィール更新に失敗しました: {str(e)}")

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """パスワード変更"""
    from services.auth_service import verify_password
    
    # 現在のパスワード確認
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="現在のパスワードが正しくありません"
        )
    
    # 新しいパスワード設定
    current_user.hashed_password = get_password_hash(new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "パスワードを変更しました"}

@router.get("/storage-info")
async def get_storage_info(
    current_user: User = Depends(get_current_user)
):
    """ストレージ使用状況取得"""
    return {
        "used_mb": current_user.storage_used_mb,
        "quota_mb": current_user.storage_quota_mb,
        "used_gb": round(current_user.storage_used_mb / 1024, 2),
        "quota_gb": round(current_user.storage_quota_mb / 1024, 2),
        "usage_percentage": round(
            (current_user.storage_used_mb / current_user.storage_quota_mb) * 100, 1
        ) if current_user.storage_quota_mb > 0 else 0
    }