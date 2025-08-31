# Render 환경 변수 설정 가이드

## 설정해야 할 환경 변수

Render 대시보드 (https://dashboard.render.com) 에서 다음 환경 변수를 추가하세요:

### 1. 데이터베이스 설정
```
DATABASE_URL=sqlite:///./video_accounting.db
```
또는 PostgreSQL을 사용하는 경우:
```
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### 2. 보안 키 (필수)
```
SECRET_KEY=n-gwncPQBQbKSbvQGiTfYUh2ey_2IG5sXhvuORxFFi0
```

### 3. 스토리지 설정
```
STORAGE_TYPE=local
```

### 4. Supabase 설정 (선택사항 - 클라우드 스토리지 사용시)
```
SUPABASE_URL=https://cphbbpvhfbmwqkcrhhwm.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNwaGJicHZoZmJtd3FrY3JoaHdtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ3ODA0MzksImV4cCI6MjA1MDM1NjQzOX0.5ivGPDz_7dTR_5q4dAjtEFMYGXKzfFPh94qQX_3CKnI
```

## 설정 방법

1. [Render Dashboard](https://dashboard.render.com) 접속
2. 해당 서비스 선택 (video-accounting-app)
3. 왼쪽 메뉴에서 "Environment" 클릭
4. "Add Environment Variable" 버튼 클릭
5. 위의 키-값 쌍을 하나씩 추가
6. "Save Changes" 클릭

## 배포 후 확인

환경 변수 설정 후 자동으로 재배포가 시작됩니다.

### 테스트 방법

1. 로그인 테스트:
```bash
curl -X POST https://video-accounting-app.onrender.com/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

2. API 상태 확인:
```bash
curl https://video-accounting-app.onrender.com/health
```

## 기본 관리자 계정
- Username: `admin`
- Password: `admin123`

⚠️ **중요**: 프로덕션 환경에서는 반드시 admin 패스워드를 변경하세요!