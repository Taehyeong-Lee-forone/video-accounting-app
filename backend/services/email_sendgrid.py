"""
SendGridを使用したメール送信サービス
"""
import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SendGridEmailService:
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@video-accounting.com")
        self.from_name = "動画会計アプリ"
        self.app_url = os.getenv("FRONTEND_URL", "https://video-accounting-app.vercel.app")
        
        # SendGrid利用可能かチェック
        self.sendgrid_available = False
        if self.api_key:
            try:
                import sendgrid
                self.sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
                self.sendgrid_available = True
                logger.info("SendGrid初期化成功")
            except ImportError:
                logger.warning("SendGridライブラリが見つかりません。pip install sendgrid を実行してください。")
            except Exception as e:
                logger.error(f"SendGrid初期化エラー: {e}")
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """
        SendGridでメールを送信
        """
        if not self.sendgrid_available:
            logger.error("SendGridが利用できません")
            return False
        
        try:
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            message = Mail()
            message.from_email = Email(self.from_email, self.from_name)
            message.to = To(to_email)
            message.subject = subject
            
            if text_content:
                message.content = [
                    Content("text/plain", text_content),
                    Content("text/html", html_content)
                ]
            else:
                message.content = Content("text/html", html_content)
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"SendGridメール送信成功: {to_email} (status: {response.status_code})")
                return True
            else:
                logger.error(f"SendGridメール送信失敗: status={response.status_code}, body={response.body}")
                return False
                
        except Exception as e:
            logger.error(f"SendGridメール送信エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def send_password_reset_email(self, to_email: str, reset_token: str, username: str) -> bool:
        """
        パスワードリセットメールを送信
        """
        reset_url = f"{self.app_url}/reset-password?token={reset_token}"
        
        subject = f"【{self.from_name}】パスワードリセットのご案内"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 12px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{self.from_name}</h1>
                    <p>パスワードリセットのご案内</p>
                </div>
                <div class="content">
                    <p>こんにちは、{username} 様</p>
                    
                    <p>パスワードリセットのリクエストを受け付けました。</p>
                    <p>以下のボタンをクリックして、新しいパスワードを設定してください。</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">パスワードをリセット</a>
                    </div>
                    
                    <p>または、以下のURLをブラウザにコピー＆ペーストしてください：</p>
                    <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px;">
                        {reset_url}
                    </p>
                    
                    <div class="warning">
                        <strong>⚠️ 注意事項</strong>
                        <ul style="margin: 5px 0;">
                            <li>このリンクは24時間有効です</li>
                            <li>心当たりがない場合は、このメールを無視してください</li>
                            <li>パスワードは変更されません</li>
                        </ul>
                    </div>
                    
                    <div class="footer">
                        <p>このメールは自動送信されています。</p>
                        <p>&copy; 2024 {self.from_name}. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {username} 様
        
        パスワードリセットのリクエストを受け付けました。
        
        以下のURLにアクセスして、新しいパスワードを設定してください：
        {reset_url}
        
        このリンクは24時間有効です。
        
        心当たりがない場合は、このメールを無視してください。
        パスワードは変更されません。
        
        ---
        {self.from_name}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)