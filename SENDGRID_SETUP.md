# SendGrid 설정 가이드

## 📧 SendGrid 무료 계정 설정 방법

### 1. SendGrid 계정 생성
1. https://sendgrid.com 접속
2. "Start For Free" 클릭
3. 이메일, 비밀번호 입력하여 가입
4. 이메일 인증 완료

### 2. API Key 생성
1. SendGrid 대시보드 로그인
2. Settings → API Keys
3. "Create API Key" 클릭
4. API Key 이름 입력 (예: video-accounting-app)
5. Full Access 선택
6. Create & View 클릭
7. **API Key 복사 (한 번만 표시됨!)**

### 3. Sender 인증
1. Settings → Sender Authentication
2. Single Sender Verification 선택 (도메인이 없는 경우)
3. 발신자 이메일 정보 입력:
   - From Email: noreply@your-domain.com 또는 Gmail 주소
   - From Name: 동영상 회계 앱
4. 인증 이메일 확인

### 4. 환경변수 설정

#### 로컬 개발 (.env)
```bash
# SendGrid 설정
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=noreply@your-domain.com

# Gmail 설정 (백업용)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=forone.video2@gmail.com
SMTP_PASSWORD=ujqbdsagmerfbnvp
```

#### Render 프로덕션
1. Render 대시보드 → Service → Environment
2. 다음 환경변수 추가:
   - `SENDGRID_API_KEY`: SendGrid API 키
   - `FROM_EMAIL`: 발신자 이메일

### 5. Python 패키지 설치
```bash
pip install sendgrid
```

### 6. requirements.txt 업데이트
```txt
sendgrid==6.11.0
```

## 🧪 테스트 방법

### 로컬 테스트
```bash
# 환경변수 설정 후
python3 test_prod_email.py
```

### 프로덕션 테스트
```bash
curl -X POST https://video-accounting-app.onrender.com/api/test/send-email \
  -H "Content-Type: application/json" \
  -d '{"to_email": "ritehyon@gmail.com"}'
```

## 📊 SendGrid 무료 플랜 제한
- 하루 100개 이메일 무료
- 월 3,000개 이메일 제한 (처음 30일)
- 이후 월 100개 이메일

## 🔄 Gmail 폴백
SendGrid가 실패하면 자동으로 Gmail SMTP로 폴백됩니다.

## ✅ 체크리스트
- [ ] SendGrid 계정 생성
- [ ] API Key 발급
- [ ] Sender 인증 완료
- [ ] 환경변수 설정
- [ ] sendgrid 패키지 설치
- [ ] 테스트 메일 발송 확인