# 📧 Outlook 메일 설정 (2단계 인증 불필요)

## Outlook 계정으로 이메일 설정

### Step 1: Outlook 계정 생성
1. https://outlook.com 접속
2. "무료 계정 만들기" 클릭
3. 이메일 주소 생성:
   - 예: `forone.video@outlook.com`
   - 또는: `video-accounting-app@outlook.com`

### Step 2: SMTP 설정 활성화
1. https://account.microsoft.com/security 접속
2. "고급 보안 옵션" 클릭
3. "앱 암호" 섹션에서:
   - "앱 암호 만들기" 클릭
   - 생성된 암호 저장

### Step 3: backend/.env 파일 설정
```bash
# Outlook SMTP 설정
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=forone.video@outlook.com
SMTP_PASSWORD=your-outlook-password  # 일반 비밀번호 또는 앱 암호
FROM_EMAIL=forone.video@outlook.com
FRONTEND_URL=https://video-accounting-app.vercel.app
```

### Step 4: 테스트
```bash
python3 test_email.py
```

## 장점
- ✅ 2단계 인증 없이 사용 가능
- ✅ 무료
- ✅ 안정적인 Microsoft 인프라
- ✅ 일일 발송 한도: 300개

## 단점
- ⚠️ Gmail보다 약간 느릴 수 있음
- ⚠️ 스팸 필터가 더 엄격할 수 있음