# 배포 가이드

## Render 백엔드 환경변수 설정 (중요!)

### 필수 환경변수

1. **GOOGLE_APPLICATION_CREDENTIALS_JSON** 
   - key_base64.txt 파일의 내용 전체를 복사하여 붙여넣기
   - Base64로 인코딩된 Google Cloud 서비스 계정 키

2. **GEMINI_API_KEY**
   - AIzaSyDENUSgUQmX-djM2TqV9S8D58BdgSANNYw

3. 기타 환경변수는 .env 파일 참조

## Render 대시보드에서 설정하는 방법

1. https://dashboard.render.com 접속
2. 백엔드 서비스 선택
3. Environment 탭 클릭
4. Add Environment Variable 클릭
5. GOOGLE_APPLICATION_CREDENTIALS_JSON 추가
6. Save Changes

이 설정이 없으면 OCR이 작동하지 않습니다!
