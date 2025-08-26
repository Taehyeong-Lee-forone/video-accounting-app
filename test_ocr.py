#!/usr/bin/env python3
"""
OCR vendor extraction 테스트 스크립트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.vision_ocr import VisionOCRService
import asyncio
import json

async def test_ocr():
    # 테스트할 이미지 경로
    test_images = [
        "/var/folders/9v/7xddtc712sn_2jgmv1x15tcc0000gn/T/TemporaryItems/NSIRD_screencaptureui_nwA86h/スクリーンショット 2025-08-25 15.19.57.png",
        "/var/folders/9v/7xddtc712sn_2jgmv1x15tcc0000gn/T/TemporaryItems/NSIRD_screencaptureui_0xFRqH/スクリーンショット 2025-08-25 15.11.56.png"
    ]
    
    service = VisionOCRService()
    
    for img_path in test_images:
        if os.path.exists(img_path):
            print(f"\n{'='*60}")
            print(f"Testing: {os.path.basename(img_path)}")
            print('='*60)
            
            try:
                # OCR 실행
                ocr_result = service.extract_text_from_image(img_path)
                full_text = ocr_result.get('full_text', '')
                
                print("\n[RAW OCR TEXT]")
                print("-" * 40)
                # 첫 10줄만 출력
                lines = full_text.split('\n')[:10]
                for i, line in enumerate(lines, 1):
                    print(f"{i:2}: {line}")
                
                # vendor 추출 테스트
                print("\n[VENDOR EXTRACTION TEST]")
                print("-" * 40)
                
                # 제외 키워드 체크
                lines = full_text.split('\n')
                exclude_keywords = ['日', '月', '年']  # 문제가 될 수 있는 키워드들
                
                for i, line in enumerate(lines[:10]):
                    if '様' in line and line.strip() == '様' and i > 0:
                        prev = lines[i-1].strip()
                        print(f"Found 様 at line {i+1}, previous line: '{prev}'")
                        for kw in exclude_keywords:
                            if kw in prev:
                                print(f"  - Contains excluded keyword: '{kw}'")
                        print(f"  - Length: {len(prev)}")
                        print(f"  - Is digit: {prev.isdigit()}")
                
                # _extract_vendor 직접 호출
                vendor = service._extract_vendor(full_text)
                print(f"\nDirect extraction: {vendor}")
                
                # parse_receipt_data 전체 호출
                parsed = service.parse_receipt_data(ocr_result)
                vendor_from_parse = parsed.get('vendor')
                print(f"From parse_receipt_data: {vendor_from_parse}")
                
                # 디버깅 정보
                print("\n[DEBUG INFO]")
                print("-" * 40)
                # "様"이 포함된 줄 찾기
                for i, line in enumerate(full_text.split('\n')[:10], 1):
                    if '様' in line:
                        print(f"Line {i} with 様: {line}")
                        
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"File not found: {img_path}")

if __name__ == "__main__":
    asyncio.run(test_ocr())