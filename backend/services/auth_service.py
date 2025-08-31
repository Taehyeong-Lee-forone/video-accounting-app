"""
認証サービス
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import os
import secrets

from database import get_db
from models import User, UserSession

# セキュリティ設定
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワード検証"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """パスワードハッシュ化"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """アクセストークン生成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """リフレッシュトークン生成"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    現在のユーザーを取得
    JWTトークンから認証
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報を確認できませんでした",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="アカウントが無効です"
        )
    
    return user

def authenticate_user(
    db: Session,
    username_or_email: str,
    password: str
) -> Optional[User]:
    """
    ユーザー認証（ユーザー名またはメールアドレスで認証）
    """
    # ユーザー名またはメールアドレスで検索
    user = db.query(User).filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_user(
    db: Session,
    email: str,
    username: str,
    password: str,
    full_name: str = None
) -> User:
    """
    新規ユーザー作成
    """
    # 既存チェック
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=400,
            detail="このメールアドレスは既に登録されています"
        )
    
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=400,
            detail="このユーザー名は既に使用されています"
        )
    
    # ユーザー作成
    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash(password),
        full_name=full_name
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

def create_session(
    db: Session,
    user: User,
    ip_address: str = None,
    user_agent: str = None
) -> UserSession:
    """
    ユーザーセッション作成
    """
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    session = UserSession(
        user_id=user.id,
        session_token=session_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

def get_user_by_session(
    db: Session,
    session_token: str
) -> Optional[User]:
    """
    セッショントークンからユーザー取得
    """
    session = db.query(UserSession).filter(
        UserSession.session_token == session_token,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if not session:
        return None
    
    # 最終アクティビティ更新
    session.last_activity = datetime.utcnow()
    db.commit()
    
    return session.user