# 영구 저장소 가이드 (Supabase Storage)

## 현재 상황
**이미 Supabase Storage를 사용 중입니다!** Supabase Storage는 영구 저장소이므로 Render를 재배포해도 파일이 사라지지 않습니다.

## Supabase Storage 확인사항

### 1. 환경 변수 확인 (Render.com)
Render 대시보드에서 다음 환경 변수가 설정되어 있는지 확인:
- `STORAGE_TYPE=supabase`
- `SUPABASE_URL=https://cphbbpvhfbmwqkcrhhwm.supabase.co`
- `SUPABASE_ANON_KEY=your_anon_key`
- `SUPABASE_BUCKET=videos`

### 2. Supabase 버킷 확인
1. [Supabase Dashboard](https://app.supabase.com/project/cphbbpvhfbmwqkcrhhwm/storage/buckets) 접속
2. 'videos' 버킷이 있는지 확인
3. 버킷이 없다면 생성:
   - 버킷 이름: `videos`
   - Public: No (프라이빗 버킷)
   - 파일 크기 제한: 100MB

### 3. 버킷 정책 확인
Supabase Dashboard > Storage > videos 버킷 > Policies 탭에서:
- **INSERT 정책**: 인증된 사용자가 업로드 가능
- **SELECT 정책**: 인증된 사용자가 조회 가능
- **DELETE 정책**: 인증된 사용자가 삭제 가능

## 문제 해결

### 파일이 여전히 사라진다면?

1. **로컬 파일 시스템 사용 확인**
   ```python
   # backend/routers/videos_v2.py 확인
   # cloud_url이 제대로 저장되고 사용되는지 확인
   ```

2. **데이터베이스 확인**
   - Video 테이블의 `cloud_url` 컬럼에 Supabase URL이 저장되는지 확인
   - 로컬 파일 경로 대신 cloud_url을 사용하는지 확인

3. **업로드 로직 확인**
   ```python
   # 올바른 예시
   success, url = storage_service.upload_file(...)
   video.cloud_url = url  # Supabase URL 저장
   
   # 잘못된 예시
   video.local_path = "/tmp/video.mp4"  # 이것은 재배포시 사라짐
   ```

## Supabase vs Cloudinary

| 특징 | Supabase Storage | Cloudinary |
|-----|-----------------|------------|
| **현재 사용 여부** | ✅ 사용 중 | ❌ 미사용 |
| **무료 용량** | 1GB | 10GB |
| **월 대역폭** | 2GB | 25GB |
| **추가 설정** | 불필요 | API 키 필요 |
| **권장사항** | 소규모 프로젝트 | 대용량 미디어 |

## 권장사항

### 현재 Supabase로 충분한 경우:
- **그대로 사용** - 추가 설정 불필요
- 이미 영구 저장소이므로 재배포해도 파일 유지됨

### 더 많은 용량이 필요한 경우:
1. Supabase 유료 플랜 업그레이드 (월 $25)
2. 또는 Cloudinary로 전환:
   ```bash
   # .env 파일에서
   STORAGE_TYPE=cloudinary
   CLOUDINARY_CLOUD_NAME=your_name
   CLOUDINARY_API_KEY=your_key
   CLOUDINARY_API_SECRET=your_secret
   ```

## 테스트 방법

1. **현재 설정 테스트**
   ```bash
   # 백엔드 실행
   cd backend
   uvicorn main:app --reload --port 5001
   ```

2. **파일 업로드**
   - 프론트엔드에서 영상 업로드
   - Supabase Dashboard > Storage에서 파일 확인

3. **영구성 테스트**
   - Render 재배포
   - 업로드된 파일이 유지되는지 확인

## 결론
**Supabase Storage를 이미 사용 중이므로 추가 설정 없이 영구 저장이 가능합니다.** 
파일이 사라지는 문제가 있다면 코드에서 로컬 파일 경로 대신 cloud_url을 사용하는지 확인하세요.