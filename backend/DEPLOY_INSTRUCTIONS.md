# 배포 및 데이터베이스 설정 가이드

## 현재 아키텍처

### 스토리지
- **Supabase Storage**: 모든 환경에서 동영상과 프레임 파일 저장
- **장점**: 영구 저장, 어디서든 접근 가능

### 데이터베이스
- **로컬 개발**: SQLite (빠른 개발과 테스트)
- **프로덕션 (Render)**: PostgreSQL (자동 관리)

## Render 환경변수 설정

Render Dashboard에서 다음 환경변수를 설정하세요:

```
# 필수 환경변수
DATABASE_URL=<Render가 자동으로 제공>
STORAGE_TYPE=supabase
SUPABASE_URL=https://cphbbpvhfbmwqkcrhhwm.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNwaGJicHZoZmJtd3FrY3JoaHdtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ3ODA0MzksImV4cCI6MjA1MDM1NjQzOX0.5ivGPDz_7dTR_5q4dAjtEFMYGXKzfFPh94qQX_3CKnI
SUPABASE_BUCKET=videos
SECRET_KEY=VP2_2UcE9rbbkjNZDbur6N4exSQSj2Izj1A_rEjRufg
JWT_SECRET=VP2_2UcE9rbbkjNZDbur6N4exSQSj2Izj1A_rEjRufg
GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/key.json
GEMINI_API_KEY=AIzaSyDENUSgUQmX-djM2TqV9S8D58BdgSANNYw
GCP_PROJECT_ID=clean-framework-468412-v2
USE_VISION_API=true
```

## 데이터 동기화 전략

### 옵션 1: 환경별 독립 운영 (현재)
- 로컬과 프로덕션이 각각 별도의 데이터베이스 사용
- 파일은 Supabase Storage로 공유

### 옵션 2: 데이터 동기화 (수동)
1. 로컬 데이터를 JSON으로 내보내기
2. 프로덕션 API를 통해 업로드

### 옵션 3: 완전 통합 (향후)
- 모든 환경에서 같은 PostgreSQL 사용
- Supabase 또는 Render PostgreSQL 선택

## 배포 체크리스트

1. [ ] 코드 변경사항 커밋
2. [ ] GitHub에 푸시
3. [ ] Render 자동 배포 확인
4. [ ] 프로덕션 테스트
   - [ ] 파일 업로드
   - [ ] 동영상 재생
   - [ ] 영수증 추출
   - [ ] 仕訳 생성

## 트러블슈팅

### 파일이 표시되지 않음
- Supabase Storage URL 확인
- CORS 설정 확인

### 데이터베이스 연결 실패
- DATABASE_URL 환경변수 확인
- SSL 설정 확인

### 로그인 문제
- JWT_SECRET 일치 확인
- 쿠키 설정 확인