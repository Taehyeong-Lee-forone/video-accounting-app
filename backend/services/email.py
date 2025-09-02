"""
メール送信サービス
"""
import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Gmail設定（環境変数から取得）
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")  # Gmailアドレス
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")  # アプリパスワード
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.app_name = "動画会計アプリ"
        self.app_url = os.getenv("FRONTEND_URL", "https://video-accounting-app.vercel.app")
        
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """
        メールを送信する
        """
        try:
            # メッセージの作成
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.app_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # テキストパート（HTMLが表示できない場合のフォールバック）
            if text_content:
                part_text = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(part_text)
            
            # HTMLパート
            part_html = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part_html)
            
            # SMTP接続と送信
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # TLS暗号化を有効化
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"メール送信成功: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"メール送信失敗: {e}")
            return False
    
    def send_password_reset_email(self, to_email: str, reset_token: str, username: str) -> bool:
        """
        パスワードリセットメールを送信
        """
        reset_url = f"{self.app_url}/reset-password?token={reset_token}"
        
        subject = f"【{self.app_name}】パスワードリセットのご案内"
        
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
                    <h1>{self.app_name}</h1>
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
                    
                    <p>ご不明な点がございましたら、お気軽にお問い合わせください。</p>
                    
                    <div class="footer">
                        <p>このメールは自動送信されています。返信はできません。</p>
                        <p>&copy; 2024 {self.app_name}. All rights reserved.</p>
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
        {self.app_name}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_welcome_email(self, to_email: str, username: str) -> bool:
        """
        ウェルカムメールを送信
        """
        subject = f"【{self.app_name}】ご登録ありがとうございます"
        
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
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>ようこそ！</h1>
                    <p>{self.app_name}へのご登録ありがとうございます</p>
                </div>
                <div class="content">
                    <p>{username} 様</p>
                    <p>アカウントの登録が完了しました。</p>
                    <p>早速、動画から領収書を抽出して、会計処理を効率化しましょう！</p>
                    
                    <div style="text-align: center;">
                        <a href="{self.app_url}" class="button">アプリを開く</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        {username} 様
        
        {self.app_name}へのご登録ありがとうございます。
        アカウントの登録が完了しました。
        
        アプリはこちら: {self.app_url}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)

# シングルトンインスタンス
email_service = EmailService()