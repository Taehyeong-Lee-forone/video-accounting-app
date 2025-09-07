# Gmail SMTP 설정 체크리스트

## 📧 Gmail 계정 설정 확인 사항

### 1. 2단계 인증 활성화 ✅
- https://myaccount.google.com/security 접속
- 2단계 인증이 활성화되어 있는지 확인

### 2. 앱 비밀번호 설정 ✅ 
- 발급된 앱 비밀번호: `ujqb dsag merf bnvp`
- 계정: `forone.video2@gmail.com`

### 3. Gmail 추가 설정 필요 사항

#### 옵션 A: Less Secure Apps (권장하지 않음)
- 2단계 인증이 활성화되어 있으면 사용 불가

#### 옵션 B: OAuth 2.0 설정 (보안 권장)
1. Google Cloud Console 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. Gmail API 활성화
4. OAuth 2.0 자격 증명 생성

#### 옵션 C: SendGrid 또는 다른 이메일 서비스 사용
- SendGrid 무료 플랜: 하루 100개 이메일
- Mailgun 무료 플랜 가능
- AWS SES (유료)

## 🔍 현재 문제 진단

### 프로덕션 환경에서 확인된 사항:
- ✅ ritehyon@gmail.com 사용자 존재
- ✅ API 응답 성공 (200 OK)
- ❌ 실제 메일 미전송

### 가능한 원인:
1. **Gmail 보안 정책**: 새로운 위치/앱에서의 로그인 차단
2. **Render IP 차단**: Render 서버 IP가 의심스러운 활동으로 차단
3. **앱 비밀번호 권한 부족**: 메일 발송 권한이 없을 수 있음

## 📝 테스트 방법

### 1. Gmail 계정 보안 활동 확인
- https://myaccount.google.com/security-checkup 접속
- 최근 보안 활동에서 차단된 로그인 시도 확인

### 2. Gmail 설정에서 IMAP/SMTP 활성화
- Gmail 설정 → 전달 및 POP/IMAP
- IMAP 사용 설정 활성화
- 변경사항 저장

### 3. Google 계정 보안 수준 일시 낮춤 (테스트용)
- https://myaccount.google.com/lesssecureapps
- (2단계 인증 비활성화 필요)

## 🚀 대안: SendGrid 설정 방법

```bash
# SendGrid 가입 후
pip install sendgrid

# 환경변수 설정
SENDGRID_API_KEY=your_api_key
```

```python
import sendgrid
from sendgrid.helpers.mail import Mail

def send_email_sendgrid(to_email, subject, content):
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    message = Mail(
        from_email='noreply@video-accounting.com',
        to_emails=to_email,
        subject=subject,
        html_content=content
    )
    response = sg.send(message)
    return response.status_code == 202
```

## 📌 권장 사항

1. **즉시 해결**: Gmail 설정에서 IMAP 활성화 확인
2. **중기 해결**: SendGrid 무료 계정으로 전환
3. **장기 해결**: 프로덕션용 전용 이메일 서비스 구축