# Render환경에서 PostgreSQL Enum 마이그레이션 가이드

## 문제 상황
- 로컬 코드는 `VideoStatus.QUEUED = "queued"`로 수정되었음
- 하지만 PostgreSQL 데이터베이스의 enum 타입은 여전히 'QUEUED' (대문자) 값을 가지고 있음
- Render 배포 시 enum 값 불일치로 인한 오류 발생

## 해결 방법

### 1. 현재 상태 확인 (옵션)
```bash
# Render Shell 또는 로컬에서 실행
python check_enum_status.py
```

### 2. 마이그레이션 실행

#### 방법 A: Render Shell 사용 (권장)
1. Render Dashboard → Services → video-accounting-api
2. "Shell" 탭 클릭
3. 다음 명령어 실행:
```bash
cd /app
python migrate_enum_values.py  # dry-run으로 먼저 확인
python migrate_enum_values.py --apply  # 실제 적용
```

#### 방법 B: 로컬에서 Production DB에 직접 연결
```bash
# .env 파일에 Supabase DATABASE_URL 설정 후
python migrate_enum_values.py  # dry-run 확인
python migrate_enum_values.py --apply  # 실제 적용
```

#### 방법 C: Supabase SQL Editor 사용
Supabase Dashboard → SQL Editor에서 직접 실행:

```sql
-- 1. 새 enum 값 추가 (이미 존재하는 경우 에러 무시)
ALTER TYPE video_status ADD VALUE IF NOT EXISTS 'queued';

-- 2. 기존 데이터 업데이트
UPDATE videos SET status = 'queued'::video_status 
WHERE status = 'QUEUED'::video_status;

-- 3. 결과 확인
SELECT status, COUNT(*) FROM videos GROUP BY status;
```

### 3. 마이그레이션 검증
```bash
# 다시 상태 확인
python check_enum_status.py
```

## 예상 결과
- 'QUEUED' 값을 가진 모든 레코드가 'queued'로 변경됨
- 새로운 비디오 업로드 시 'queued' 값으로 정상 저장
- Render 배포 에러 해결

## 주의사항
- 마이그레이션 중에는 잠시 서비스가 불안정할 수 있음
- 반드시 dry-run으로 먼저 확인 후 적용
- 백업이 있다면 마이그레이션 전 백업 권장