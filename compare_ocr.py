#!/usr/bin/env python3
"""
OCR 성능 비교 스크립트
Vision API vs Gemini 비교
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.vision_ocr import VisionOCRService
import asyncio

async def compare_ocr():
    # 테스트 이미지
    test_image = "/var/folders/9v/7xddtc712sn_2jgmv1x15tcc0000gn/T/TemporaryItems/NSIRD_screencaptureui_0xFRqH/スクリーンショット 2025-08-25 15.11.56.png"
    
    if not os.path.exists(test_image):
        print("테스트 이미지를 찾을 수 없습니다.")
        return
    
    print("=" * 60)
    print("OCR 성능 비교 테스트")
    print("=" * 60)
    
    # Vision API 테스트
    print("\n[Google Cloud Vision API]")
    print("-" * 40)
    try:
        vision_service = VisionOCRService()
        ocr_result = vision_service.extract_text_from_image(test_image)
        full_text = ocr_result.get('full_text', '')
        
        # 첫 5줄 출력
        lines = full_text.split('\n')[:5]
        for i, line in enumerate(lines, 1):
            print(f"{i}: {line}")
        
        # vendor 추출 테스트
        parsed = vision_service.parse_receipt_data(ocr_result)
        print(f"\n추출된 vendor: {parsed.get('vendor')}")
        print(f"추출된 금액: ¥{parsed.get('total', 0):,.0f}")
        
    except Exception as e:
        print(f"Vision API 오류: {e}")
    
    print("\n" + "=" * 60)
    print("Vision API 개선 제안:")
    print("1. 이미지 전처리 추가 (contrast, sharpness)")
    print("2. 해상도 향상 (upscaling)")
    print("3. 언어 힌트 최적화 완료")
    print("4. Gemini Vision으로 전환 고려")

if __name__ == "__main__":
    asyncio.run(compare_ocr())