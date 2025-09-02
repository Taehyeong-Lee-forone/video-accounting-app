# Gmail 메일 송신 설정 가이드

## 📧 Gmail 앱 패스워드 생성 방법

### 1단계: Google 계정 보안 설정
1. Google 계정에 로그인
2. https://myaccount.google.com/security 접속
3. "로그인 및 보안" 섹션 확인

### 2단계: 2단계 인증 활성화
1. "Google에 로그인" 섹션에서 "2단계 인증" 클릭
2. 아직 활성화되지 않았다면 설정 진행
3. 전화번호 인증 완료

### 3단계: 앱 패스워드 생성
1. 2단계 인증 활성화 후, 보안 페이지로 돌아가기
2. "앱 패스워드" 선택 (2단계 인증이 활성화되어야 표시됨)
3. 앱 선택: "기타(맞춤 이름)"
4. 이름 입력: "video-accounting-app"
5. "생성" 클릭
6. **16자리 패스워드가 표시됨** (예: abcd efgh ijkl mnop)
7. 이 패스워드를 복사 (공백 제거)

### 4단계: .env 파일 업데이트

```bash
# 메일 설정 (Gmail용)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@gmail.com  # 본인의 Gmail 주소
SMTP_PASSWORD=abcdefghijklmnop   # 생성한 16자리 앱 패스워드 (공백 없이)
FROM_EMAIL=your.email@gmail.com  # 본인의 Gmail 주소
FRONTEND_URL=https://video-accounting-app.vercel.app

# 데모모드 비활성화 (실제 메일 송신)
DEMO_MODE=false
```

### 5단계: 테스트
```bash
# 테스트 스크립트 실행
python3 test_email.py
```

## ⚠️ 주의사항
- **앱 패스워드는 일반 Gmail 비밀번호와 다릅니다**
- 2단계 인증이 먼저 활성화되어야 앱 패스워드를 생성할 수 있습니다
- 앱 패스워드는 안전하게 보관하세요
- 패스워드에 공백이 포함되지 않도록 주의하세요

## 🔍 문제 해결
- **"앱 패스워드" 메뉴가 보이지 않는 경우**: 2단계 인증을 먼저 활성화하세요
- **인증 실패**: 앱 패스워드가 정확히 16자리인지, 공백이 없는지 확인하세요
- **메일이 스팸함으로 가는 경우**: Gmail 설정에서 발신자를 안전한 발신자로 추가하세요