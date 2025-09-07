# 📧 SendGrid 이메일 설정 (무료, 전문적)

## SendGrid란?
전문 이메일 발송 서비스로, 개발자를 위한 API 제공

## 무료 플랜
- 일일 100개 이메일 무료
- 2단계 인증 불필요
- 상세한 분석 기능

## 설정 방법

### Step 1: SendGrid 계정 생성
1. https://signup.sendgrid.com/ 접속
2. 무료 계정 생성
3. 이메일 인증 완료

### Step 2: API 키 생성
1. Settings → API Keys
2. "Create API Key" 클릭
3. Full Access 선택
4. API 키 복사 (한 번만 표시됨!)

### Step 3: 발신자 인증
1. Settings → Sender Authentication
2. "Single Sender Verification" 선택
3. 발신 이메일 추가: `forone.video2@gmail.com`
4. 인증 메일 확인

### Step 4: 코드 수정

**backend/services/email_sendgrid.py** 생성:
```python
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "forone.video2@gmail.com")
        self.app_name = "動画会計アプリ"
        self.app_url = os.getenv("FRONTEND_URL", "https://video-accounting-app.vercel.app")
        
    def send_email(self, to_email: str, subject: str, html_content: str, text_content=None):
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            logger.info(f"メール送信成功: {to_email}")
            return True
        except Exception as e:
            logger.error(f"メール送信失敗: {e}")
            return False
    
    def send_password_reset_email(self, to_email: str, reset_token: str, username: str):
        # 既存のHTMLテンプレートと同じ
        reset_url = f"{self.app_url}/reset-password?token={reset_token}"
        subject = f"【{self.app_name}】パスワードリセットのご案内"
        
        html_content = f"""
        <h2>パスワードリセット</h2>
        <p>{username} 様</p>
        <p>以下のリンクから新しいパスワードを設定してください：</p>
        <a href="{reset_url}">パスワードをリセット</a>
        <p>このリンクは24時間有効です。</p>
        """
        
        return self.send_email(to_email, subject, html_content)

email_service = EmailService()
```

### Step 5: 환경 변수 설정

**backend/.env:**
```bash
# SendGrid 설정
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=forone.video2@gmail.com
FRONTEND_URL=https://video-accounting-app.vercel.app
```

### Step 6: 패키지 설치
```bash
pip install sendgrid
```

## 장점
- ✅ 2단계 인증 불필요
- ✅ 전문적인 이메일 전송
- ✅ 상세한 통계 (열람률, 클릭률 등)
- ✅ 높은 전달률
- ✅ 무료 100개/일

## 단점
- ⚠️ API 키 관리 필요
- ⚠️ 100개/일 초과 시 유료