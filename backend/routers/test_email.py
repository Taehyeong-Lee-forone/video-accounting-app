"""
メール送信テスト用エンドポイント（デバッグ用）
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.email import email_service
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

class TestEmailRequest(BaseModel):
    to_email: str = "ritehyon@gmail.com"

@router.post("/api/test/send-email")
async def test_send_email(request: TestEmailRequest):
    """
    テスト用メール送信エンドポイント
    """
    try:
        # 環境変数の確認
        env_info = {
            "RENDER": os.getenv("RENDER"),
            "SMTP_HOST": os.getenv("SMTP_HOST"),
            "SMTP_USER": os.getenv("SMTP_USER"),
            "SMTP_PASSWORD": "***" if os.getenv("SMTP_PASSWORD") else None,
            "FROM_EMAIL": os.getenv("FROM_EMAIL")
        }
        
        logger.info(f"環境変数状態: {env_info}")
        
        # EmailServiceの現在の設定
        service_info = {
            "smtp_host": email_service.smtp_host,
            "smtp_port": email_service.smtp_port,
            "smtp_user": email_service.smtp_user,
            "smtp_password": "***" if email_service.smtp_password else None,
            "from_email": email_service.from_email
        }
        
        logger.info(f"EmailService設定: {service_info}")
        
        # テストメール送信
        subject = "【テスト】動画会計アプリ - メール送信テスト"
        html_content = """
        <html>
        <body>
            <h2>メール送信テスト</h2>
            <p>このメールは動画会計アプリからのテストメールです。</p>
            <p>正常にメールが届いています！</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                送信元: 動画会計アプリ<br>
                環境: プロダクション
            </p>
        </body>
        </html>
        """
        
        text_content = """
        メール送信テスト
        
        このメールは動画会計アプリからのテストメールです。
        正常にメールが届いています！
        
        ---
        動画会計アプリ
        """
        
        # メール送信実行
        success = email_service.send_email(
            to_email=request.to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        if success:
            return {
                "success": True,
                "message": f"テストメールを {request.to_email} に送信しました",
                "env_info": env_info,
                "service_info": service_info
            }
        else:
            return {
                "success": False,
                "message": "メール送信に失敗しました",
                "env_info": env_info,
                "service_info": service_info
            }
            
    except Exception as e:
        logger.error(f"テストメール送信エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/test/email-config")
async def get_email_config():
    """
    現在のメール設定を確認
    """
    return {
        "environment": {
            "RENDER": os.getenv("RENDER"),
            "SMTP_HOST": os.getenv("SMTP_HOST"),
            "SMTP_PORT": os.getenv("SMTP_PORT"),
            "SMTP_USER": os.getenv("SMTP_USER"),
            "SMTP_PASSWORD": "SET" if os.getenv("SMTP_PASSWORD") else "NOT_SET",
            "FROM_EMAIL": os.getenv("FROM_EMAIL")
        },
        "service": {
            "smtp_host": email_service.smtp_host,
            "smtp_port": email_service.smtp_port,
            "smtp_user": email_service.smtp_user,
            "smtp_password": "SET" if email_service.smtp_password else "NOT_SET",
            "from_email": email_service.from_email
        }
    }