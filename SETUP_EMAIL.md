# 📧 이메일 설정 가이드

## 전용 메일 계정 설정 (권장)

### Step 1: 전용 Gmail 계정 생성
1. https://accounts.google.com/signup 에서 새 계정 생성
2. 추천 계정명:
   - `video.accounting.noreply@gmail.com`
   - `your-app-name.notifications@gmail.com`
   - `회사명.app@gmail.com`

3. 프로필 설정:
   - 이름: `動画会計アプリ`
   - 프로필 사진: 앱 로고 (선택사항)

### Step 2: 보안 설정
1. **2단계 인증 활성화** (필수)
   - https://myaccount.google.com/security
   - "2단계 인증" → 활성화

2. **앱 비밀번호 생성**
   - https://myaccount.google.com/apppasswords
   - 앱: "메일" 선택
   - 기기: "Video Accounting App"
   - 16자리 비밀번호 저장

### Step 3: 환경 변수 설정

#### 로컬 개발 (backend/.env)
```bash
# メール送信設定
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=video.accounting.noreply@gmail.com
SMTP_PASSWORD=abcdefghijklmnop  # 16자리 앱 비밀번호 (공백 제거)
FROM_EMAIL=video.accounting.noreply@gmail.com
FRONTEND_URL=https://video-accounting-app.vercel.app
```

#### 프로덕션 (Render Dashboard)
1. https://dashboard.render.com 접속
2. 백엔드 서비스 → Environment → Environment Variables
3. 위와 동일한 변수 추가

### Step 4: 테스트
```bash
cd /Users/taehyeonglee/video-accounting-app
python3 test_email.py
```

## 이메일 템플릿 커스터마이징

발신자 표시명을 변경하려면:

**backend/services/email.py** 26번째 줄:
```python
self.app_name = "動画会計アプリ"  # 원하는 이름으로 변경
```

## 문제 해결

### "Less secure app access" 오류
- 2단계 인증이 활성화되어 있는지 확인
- 앱 비밀번호를 사용하고 있는지 확인 (일반 비밀번호 X)

### 메일이 스팸함으로 가는 경우
- SPF/DKIM 설정 (Google Workspace 필요)
- 또는 전문 이메일 서비스 고려 (SendGrid 등)

### 일일 발송 한도 (Gmail)
- 무료 계정: 500개/일
- Google Workspace: 2,000개/일
- 초과 시 SendGrid, AWS SES 고려

## 보안 주의사항
- ⚠️ `.env` 파일은 절대 Git에 커밋하지 마세요
- ⚠️ 앱 비밀번호는 안전한 곳에 별도 보관
- ⚠️ 정기적으로 앱 비밀번호 재생성 권장

## 다음 단계
1. ✅ 전용 Gmail 계정 생성
2. ✅ 2단계 인증 및 앱 비밀번호 설정
3. ✅ 환경 변수 업데이트
4. ✅ 테스트 실행
5. ✅ Render에 프로덕션 환경 변수 설정