# Cloudinary 영구 저장소 설정 가이드

## 문제점
현재 Render.com 무료 플랜을 사용 중이므로, 새로 배포할 때마다 업로드된 영상 파일이 삭제됩니다. 이는 Render의 ephemeral 파일 시스템 때문입니다.

## 해결책: Cloudinary 사용
Cloudinary는 클라우드 기반 미디어 관리 서비스로, 무료 플랜에서도 충분한 용량을 제공합니다.

### Cloudinary 무료 플랜 제공 사항
- **월 25GB 대역폭**
- **25,000개 변환 작업**
- **10GB 저장 공간**
- **자동 CDN 제공**
- **이미지/비디오 최적화**

## 설정 방법

### 1. Cloudinary 계정 생성
1. [Cloudinary 무료 가입](https://cloudinary.com/users/register/free) 페이지로 이동
2. 이메일과 비밀번호로 계정 생성
3. 이메일 인증 완료

### 2. API 키 확인
1. Cloudinary 대시보드 로그인
2. Dashboard에서 다음 정보 확인:
   - **Cloud Name**
   - **API Key**
   - **API Secret**

### 3. 환경 변수 설정

#### 로컬 개발 (.env 파일)
```bash
# Storage Configuration
STORAGE_TYPE=cloudinary

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
```

#### Render.com 프로덕션 설정
1. Render 대시보드에서 백엔드 서비스 선택
2. **Environment** 탭 이동
3. 다음 환경 변수 추가:
   - `STORAGE_TYPE` = `cloudinary`
   - `CLOUDINARY_CLOUD_NAME` = `your_cloud_name`
   - `CLOUDINARY_API_KEY` = `your_api_key`
   - `CLOUDINARY_API_SECRET` = `your_api_secret`
4. **Save Changes** 클릭

### 4. 배포 및 확인
```bash
# 변경사항 커밋
git add .
git commit -m "feat: Cloudinary 영구 저장소 구현"
git push origin main

# Render는 자동으로 재배포됨
```

### 5. 테스트
로컬에서 테스트:
```bash
python3 test_cloudinary.py
```

프로덕션 테스트:
1. https://video-accounting-app.vercel.app 접속
2. 영상 업로드
3. 페이지 새로고침 후 영상이 유지되는지 확인
4. Render 재배포 후에도 영상이 유지되는지 확인

## 장점
✅ **영구 저장**: 재배포해도 파일이 사라지지 않음
✅ **CDN 제공**: 전 세계 어디서나 빠른 로딩
✅ **자동 최적화**: 대역폭 절약
✅ **무료 플랜 충분**: 소규모 프로젝트에 적합
✅ **간단한 설정**: API 키만 있으면 즉시 사용 가능

## 주의사항
- 무료 플랜 한도 초과 시 추가 요금 발생 가능
- API Secret은 절대 공개하지 않기
- 정기적으로 사용량 모니터링 필요

## 문제 해결
테스트 실패 시:
1. API 키가 올바른지 확인
2. Cloudinary 대시보드에서 사용량 확인
3. 네트워크 연결 확인
4. 환경 변수가 제대로 설정되었는지 확인

## 대안
만약 Cloudinary를 사용하지 않으려면:
- **Supabase Storage**: 이미 Supabase 사용 중이라면 통합 가능
- **AWS S3**: 더 많은 제어가 필요한 경우
- **Google Cloud Storage**: Google Cloud 에코시스템 사용 시