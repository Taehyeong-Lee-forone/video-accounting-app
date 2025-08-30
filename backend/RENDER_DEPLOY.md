# Render 배포 가이드

## 중요: 환경 변수 설정 필수! (Render Dashboard)

⚠️ **반드시 Render Dashboard에서 환경 변수를 설정해야 합니다!**

## 환경 변수 설정 (Render Dashboard)

Render 대시보드에서 다음 환경 변수를 수동으로 설정해야 합니다:

### 필수 환경 변수

1. **데이터베이스 설정 (Supabase)**

   **옵션 1 (권장): DATABASE_URL 직접 설정**
   - `DATABASE_URL`: Supabase Dashboard > Settings > Database > Connection Pooling에서 복사
     - Mode: Transaction 선택
     - Connection string 복사
     - 예시: `postgresql://postgres.dhbzrmokkyeevuphhkrd:[YOUR-PASSWORD]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres`
   
   **옵션 2: 개별 설정**
   - `SUPABASE_URL`: 프로젝트 Reference ID (예: `dhbzrmokkyeevuphhkrd`)
   - `SUPABASE_PASSWORD`: 데이터베이스 비밀번호

2. **API 키**
   - `GEMINI_API_KEY`: Google Gemini API 키
   - `JWT_SECRET`: JWT 토큰 서명용 비밀 키 (강력한 랜덤 문자열 사용)

## Supabase 설정 확인

1. Supabase 대시보드에서 Settings > Database 로 이동
2. Connection Pooling 섹션 확인
3. Connection string > Transaction 모드 선택
4. 연결 문자열 복사

## 배포 전 체크리스트

- [ ] Supabase 데이터베이스 생성 완료
- [ ] 테이블 스키마 실행 완료 (`deployment/supabase_schema.sql`)
- [ ] 환경 변수 모두 설정 완료
- [ ] GitHub 리포지토리 연결 완료

## 배포 후 확인

1. Health Check: `https://your-app.onrender.com/health`
2. API 문서: `https://your-app.onrender.com/docs`
3. 로그 확인: Render Dashboard > Logs
4. 포트 바인딩 확인: 로그에서 "Starting server on port 10000" 메시지 확인

## 트러블슈팅

### "Network is unreachable" 또는 IPv6 연결 오류
- Supabase Connection Pooling URL 사용 (Direct connection 대신)
- Transaction mode 선택
- Pooler endpoint 사용: `aws-0-ap-northeast-2.pooler.supabase.com`

### "Tenant or user not found" 오류
- DATABASE_URL이 올바르게 설정되었는지 확인
- Supabase 대시보드에서 Connection Pooling이 활성화되어 있는지 확인
- 비밀번호에 특수문자가 있는 경우 URL 인코딩 필요

### "No open ports detected" 오류
- PORT 환경 변수가 설정되어 있는지 확인 (기본값: 10000)
- Dockerfile의 CMD가 올바른지 확인

## 로컬 테스트

```bash
# 로컬에서 Render 환경 시뮬레이션
export RENDER=true
export DATABASE_URL="your-supabase-pooler-url"
python init_db.py --render
```