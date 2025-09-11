# 🚀 GPT-4V 통합 마이그레이션 가이드

## 📋 개요
모든 OCR/Vision 처리를 GPT-4V로 통합하여 시스템을 단순화하고 정확도를 향상시킵니다.

## 🔄 변경 사항

### Before (복잡한 2단계 처리)
```
비디오 → 프레임 추출 → Google Cloud Vision (OCR) → 텍스트 → Gemini/GPT (구조화) → 결과
```
- 파일 6개, 코드 1000줄+
- 2개의 API 관리 필요
- 정확도 중간

### After (단순한 1단계 처리)
```
비디오 → 프레임 추출 → GPT-4V → 구조화된 결과
```
- 파일 2개, 코드 300줄
- 1개의 API만 사용
- 정확도 높음

## 💰 비용 비교

| 처리량 | 기존 방식 | GPT-4V | 비고 |
|--------|-----------|--------|------|
| 100장/월 | 240원 | 1,300~3,900원 | 소규모 OK |
| 300장/월 | 720원 | 3,900~11,700원 | 적정선 |
| 1000장/월 | 2,400원 | 13,000~39,000원 | 비용 고려 필요 |

## 🛠️ 설정 방법

### 1. OpenAI API 키 발급
1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭
3. 키 복사 (sk-로 시작)

### 2. 로컬 환경 설정
```bash
# backend/.env 파일 수정
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
VISION_PROVIDER=gpt4v

# 삭제 가능한 설정들
# GEMINI_API_KEY=xxx  # 더 이상 불필요
# GOOGLE_APPLICATION_CREDENTIALS=xxx  # 더 이상 불필요
```

### 3. 테스트
```bash
cd backend
python test_gpt4v.py
```

### 4. Render 프로덕션 설정
1. Render Dashboard 접속
2. Environment → Environment Variables
3. 추가:
   - `OPENAI_API_KEY` = `sk-xxxxx` (실제 키)
   - `VISION_PROVIDER` = `gpt4v`
4. 삭제 가능:
   - `GEMINI_API_KEY`
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON`

### 5. 배포
```bash
git add -A
git commit -m "feat: GPT-4V 통합 - 모든 OCR 처리 단순화"
git push origin main
```

## 📁 새로운 파일 구조

```
backend/services/
├── gpt4v_service.py          # GPT-4V 통합 서비스 (메인)
├── video_intelligence_gpt4v.py  # 비디오 처리 (GPT-4V 버전)
│
├── [삭제 예정]
├── vision_ocr.py             # Google Cloud Vision (불필요)
├── enhanced_ocr.py           # 복잡한 OCR 처리 (불필요)
├── ai_service.py             # LLM 래퍼 (불필요)
└── receipt_parser.py         # 수동 파싱 (불필요)
```

## ✅ 체크리스트

- [ ] OpenAI API 키 발급
- [ ] .env 파일에 OPENAI_API_KEY 추가
- [ ] test_gpt4v.py 실행 성공
- [ ] Render 환경변수 설정
- [ ] 프로덕션 배포
- [ ] 기존 API 키 정리 (선택)

## 🎯 예상 효과

1. **코드 단순화**: 1000줄 → 300줄
2. **정확도 향상**: 특히 수기 영수증
3. **유지보수 용이**: API 1개만 관리
4. **처리 속도**: 2단계 → 1단계로 빨라짐

## ⚠️ 주의사항

- 월 1000장 이상 처리 시 비용 급증
- API 키 노출 주의 (GitHub에 커밋 금지)
- 이미지 크기 최적화로 비용 절감 가능

## 📞 문의

문제 발생 시:
1. `test_gpt4v.py` 실행 결과 확인
2. `.env` 파일의 OPENAI_API_KEY 확인
3. Render 로그 확인