#!/usr/bin/env python3
"""
OCR 숫자 인식 문제 진단
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.vision_ocr import VisionOCRService
from PIL import Image
import cv2
import numpy as np

def analyze_image_quality(image_path):
    """이미지 품질 분석"""
    print("\n[이미지 품질 분석]")
    print("-" * 40)
    
    # PIL로 기본 정보
    img = Image.open(image_path)
    print(f"크기: {img.size[0]} x {img.size[1]} pixels")
    print(f"모드: {img.mode}")
    print(f"포맷: {img.format}")
    
    # OpenCV로 상세 분석
    cv_img = cv2.imread(image_path)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # 밝기 분석
    brightness = np.mean(gray)
    print(f"평균 밝기: {brightness:.1f}/255")
    
    # 대비 분석
    contrast = np.std(gray)
    print(f"대비 (표준편차): {contrast:.1f}")
    
    # 선명도 분석 (Laplacian)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = laplacian.var()
    print(f"선명도 점수: {sharpness:.1f}")
    
    # 권장사항
    print("\n[품질 평가]")
    if img.size[0] < 1000:
        print("⚠️ 해상도가 너무 낮습니다. 최소 1000px 이상 권장")
    if brightness < 100:
        print("⚠️ 이미지가 너무 어둡습니다")
    if contrast < 30:
        print("⚠️ 대비가 너무 낮습니다")
    if sharpness < 100:
        print("⚠️ 이미지가 흐릿합니다")

def test_enhanced_ocr(image_path):
    """개선된 OCR 테스트"""
    print("\n[이미지 전처리 및 OCR]")
    print("-" * 40)
    
    # 1. 원본 OCR
    print("\n1. 원본 이미지 OCR:")
    vision_service = VisionOCRService()
    
    try:
        result = vision_service.extract_text_from_image(image_path)
        text = result.get('full_text', '')
        
        # 숫자만 추출해서 보기
        import re
        numbers = re.findall(r'\d+[,\d]*', text)
        print(f"인식된 숫자들: {numbers[:10]}")  # 처음 10개만
        
        # 금액 패턴 찾기
        amounts = re.findall(r'[¥￥]?\s*(\d{1,3}(?:,\d{3})*)', text)
        if amounts:
            print(f"인식된 금액 패턴: {amounts[:5]}")
        
    except Exception as e:
        print(f"오류: {e}")
    
    # 2. 전처리된 이미지로 OCR (OpenCV 설치 필요)
    print("\n2. 전처리 후 OCR 테스트:")
    try:
        # 이미지 읽기
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 대비 향상 (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # 샤프닝
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # 임시 파일로 저장
        temp_path = '/tmp/enhanced_receipt.png'
        cv2.imwrite(temp_path, sharpened)
        
        # 전처리된 이미지로 OCR
        result = vision_service.extract_text_from_image(temp_path)
        text = result.get('full_text', '')
        
        numbers = re.findall(r'\d+[,\d]*', text)
        print(f"개선된 숫자 인식: {numbers[:10]}")
        
    except Exception as e:
        print(f"전처리 실패: {e}")

# 테스트 실행
if __name__ == "__main__":
    # 테스트할 이미지들
    test_images = [
        "/var/folders/9v/7xddtc712sn_2jgmv1x15tcc0000gn/T/TemporaryItems/NSIRD_screencaptureui_0xFRqH/スクリーンショット 2025-08-25 15.11.56.png",
        # 프레임 이미지가 있다면 추가
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            print("\n" + "=" * 60)
            print(f"테스트 이미지: {os.path.basename(img_path)}")
            print("=" * 60)
            
            analyze_image_quality(img_path)
            test_enhanced_ocr(img_path)
        else:
            print(f"파일을 찾을 수 없음: {img_path}")