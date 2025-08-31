# Claude 설정 규칙

## 언어 규칙
- **설명**: 모든 설명과 대화는 한국어로 작성
- **코드 주석**: 모든 코드 내 주석은 일본어로 작성

## 예시
```python
# データベース接続を初期化する
def initialize_database():
    # 設定ファイルを読み込む
    config = load_config()
    # 接続を確立する
    return connect(config)
```

## 적용 범위
- 모든 Python 파일 (.py)
- 모든 JavaScript/TypeScript 파일 (.js, .ts, .jsx, .tsx)
- 모든 설정 파일의 주석
- 기타 프로그래밍 언어 파일

## 테스트 규칙
- **중요한 변경사항이 있을 때마다 반드시 실제 파일 업로드 테스트 수행**
- **테스트 파일**: `uploads/videos/1753309926185.mp4` 사용
- **테스트 방법**: 
  1. curl 또는 Python 스크립트로 실제 파일 업로드 시도
  2. 서버 로그 확인
  3. 업로드 성공/실패 여부 확인
  4. 문제 발견 시 즉시 수정
- **테스트 완료 후에만 사용자에게 보고**

## 개발 워크플로우 자동화 규칙
- **모든 코드 변경 시 필수 수행 작업**:
  1. **커밋**: 변경사항을 명확한 메시지와 함께 Git 커밋
  2. **배포**: GitHub에 푸시하여 자동 배포 (Vercel/Render)
  3. **테스트**: 배포 서버에서 실제 동작 테스트
  4. **검증**: 에러 발생 시 즉시 수정 후 재배포

- **배포 URL**:
  - Frontend (Vercel): `https://video-accounting-app.vercel.app`
  - Backend (Render): `https://video-accounting-app.onrender.com`

- **테스트 체크리스트**:
  - [ ] 파일 업로드 동작 확인
  - [ ] 동영상 재생 확인
  - [ ] 영수증 추출 및 표시 확인
  - [ ] 仕訳 생성 확인
  - [ ] 에러 메시지 없음 확인