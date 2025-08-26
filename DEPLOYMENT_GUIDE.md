# 배포 가이드 - Video Accounting App

## 📋 Prerequisites

- Supabase 계정
- Vercel 계정  
- Railway 또는 Render 계정
- Google Cloud Vision API 키
- Git 저장소 (GitHub/GitLab)

## 🔧 Step 1: Supabase 설정

### 1.1 프로젝트 생성
1. [Supabase](https://supabase.com) 로그인
2. "New Project" 클릭
3. 프로젝트 이름: `video-accounting`
4. 데이터베이스 비밀번호 설정 (안전하게 저장!)
5. Region: `Northeast Asia (Tokyo)`

### 1.2 데이터베이스 스키마 적용
1. Supabase Dashboard → SQL Editor
2. `deployment/supabase_schema.sql` 내용 복사
3. 실행 (Run)

### 1.3 환경변수 수집
- Project URL: `https://[YOUR-PROJECT-REF].supabase.co`
- Anon Key: Settings → API → anon public
- Service Key: Settings → API → service_role  
- Database URL: Settings → Database → Connection string

### 1.4 Storage 버킷 생성
1. Storage → New bucket
2. Name: `videos`
3. Public: OFF (보안상 private 권장)

## 🚀 Step 2: Backend 배포 (Railway)

### 2.1 Railway 프로젝트 생성
```bash
# Railway CLI 설치
npm install -g @railway/cli

# 로그인
railway login

# 프로젝트 초기화
railway init
```

### 2.2 환경변수 설정
Railway Dashboard에서:
```
DATABASE_URL=[Supabase Database URL]
GOOGLE_APPLICATION_CREDENTIALS_JSON=[Base64 encoded JSON]
SUPABASE_URL=[Your Supabase URL]
SUPABASE_SERVICE_KEY=[Your Service Key]
SECRET_KEY=[Generate random key]
CORS_ORIGINS=https://your-app.vercel.app
```

### 2.3 배포
```bash
# Git push로 자동 배포
git add .
git commit -m "Deploy backend"
git push origin main

# 또는 CLI로 직접 배포
railway up
```

## 🎨 Step 3: Frontend 배포 (Vercel)

### 3.1 Vercel 프로젝트 연결
```bash
# Vercel CLI 설치
npm install -g vercel

# 프로젝트 연결
cd frontend
vercel
```

### 3.2 환경변수 설정
Vercel Dashboard → Settings → Environment Variables:
```
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_SUPABASE_URL=[Your Supabase URL]
NEXT_PUBLIC_SUPABASE_ANON_KEY=[Your Anon Key]
```

### 3.3 배포
```bash
# Production 배포
vercel --prod

# 또는 Git push로 자동 배포
git push origin main
```

## 📁 Step 4: 파일 스토리지 설정

### Option 1: Supabase Storage (권장)
Backend 코드에서:
```python
# services/storage.py 수정
STORAGE_TYPE = "supabase"
```

### Option 2: Google Cloud Storage
1. GCS 버킷 생성
2. Service Account에 권한 부여
3. 환경변수 설정:
```
STORAGE_TYPE=gcs
GCS_BUCKET_NAME=your-bucket
```

## 🔐 Step 5: Google Vision API 설정

### 5.1 Service Account 생성
1. [Google Cloud Console](https://console.cloud.google.com)
2. IAM & Admin → Service Accounts
3. Create Service Account
4. Role: Cloud Vision API User
5. Create Key (JSON)

### 5.2 JSON을 Base64로 인코딩
```bash
# macOS/Linux
base64 -i key.json -o key_base64.txt

# 또는 온라인 툴 사용
```

### 5.3 환경변수 설정
```
GOOGLE_APPLICATION_CREDENTIALS_JSON=[base64 encoded content]
```

## ✅ Step 6: 배포 확인

### 6.1 Health Check
```bash
# Backend
curl https://your-backend.railway.app/health

# Frontend  
curl https://your-app.vercel.app
```

### 6.2 데이터베이스 연결 확인
```bash
# Supabase SQL Editor에서
SELECT COUNT(*) FROM videos;
```

### 6.3 파일 업로드 테스트
1. Frontend에서 비디오 업로드
2. Supabase Storage에서 파일 확인
3. 영수증 처리 확인

## 🐛 Troubleshooting

### PostgreSQL 연결 오류
- DATABASE_URL 형식 확인
- SSL 설정: `?sslmode=require` 추가
- Supabase 방화벽 설정 확인

### CORS 오류
- Backend CORS_ORIGINS 환경변수 확인
- Frontend URL이 정확한지 확인

### Vision API 오류
- API 할당량 확인
- Service Account 권한 확인
- Base64 인코딩이 올바른지 확인

### 파일 업로드 오류
- Supabase Storage 정책(Policy) 확인
- 파일 크기 제한 확인 (기본 50MB)
- Service Key vs Anon Key 권한 차이

## 📊 모니터링

### Railway
- Metrics → CPU, Memory, Network 모니터링
- Logs → 실시간 로그 확인

### Vercel
- Analytics → 페이지 로딩 속도
- Functions → API Route 성능

### Supabase
- Database → Query Performance
- Storage → 사용량 모니터링

## 🔄 업데이트 배포

### Zero-downtime 배포
```bash
# Backend (Railway)
git push origin main  # 자동 롤링 업데이트

# Frontend (Vercel)
vercel --prod  # 자동 엣지 배포
```

### 데이터베이스 마이그레이션
```bash
# Alembic 사용
cd backend
alembic upgrade head
```

## 💰 비용 최적화

### 무료 티어 활용
- Supabase: 500MB DB, 1GB Storage
- Vercel: 100GB Bandwidth
- Railway: $5 크레딧/월

### 비용 절감 팁
1. 이미지 최적화 (WebP 변환)
2. 비디오 압축
3. 캐싱 활용
4. 불필요한 API 호출 줄이기

## 📞 지원

- Supabase Discord: https://discord.supabase.com
- Vercel Discord: https://vercel.com/discord
- Railway Discord: https://discord.gg/railway