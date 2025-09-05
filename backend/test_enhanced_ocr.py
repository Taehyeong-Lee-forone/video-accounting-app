#!/usr/bin/env python3
"""
強化版OCRのテストスクリプト
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from services.enhanced_ocr import EnhancedOCRService
from services.vision_ocr import VisionOCRService
import glob
import time

def test_enhanced_ocr():
    """強化版OCRのテスト"""
    
    print("=" * 60)
    print("Enhanced OCR Test")
    print("=" * 60)
    
    # サービスを初期化
    enhanced_ocr = EnhancedOCRService()
    vision_ocr = VisionOCRService()
    
    # テスト画像を探す
    test_images = glob.glob("uploads/frames/*.jpg") or glob.glob("backend/uploads/frames/*.jpg")
    
    if not test_images:
        print("❌ No test images found")
        return
    
    # 最初の3枚でテスト
    for image_path in test_images[:3]:
        print(f"\n{'='*40}")
        print(f"Testing: {Path(image_path).name}")
        print("="*40)
        
        # 1. 従来のVision API OCR
        print("\n📸 Traditional Vision API OCR:")
        print("-" * 30)
        start_time = time.time()
        try:
            vision_result = vision_ocr.extract_text_from_image(image_path)
            vision_time = time.time() - start_time
            
            if vision_result and vision_result.get('receipt_data'):
                receipt = vision_result['receipt_data']
                print(f"  Vendor: {receipt.get('vendor', 'N/A')}")
                print(f"  Date: {receipt.get('issue_date', 'N/A')}")
                print(f"  Total: ¥{receipt.get('total', 0):,.0f}")
                print(f"  Time: {vision_time:.2f}s")
            else:
                print("  ❌ Failed to extract data")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # 2. 強化版OCR（前処理なし）
        print("\n🚀 Enhanced OCR (no preprocessing):")
        print("-" * 30)
        start_time = time.time()
        try:
            enhanced_result = enhanced_ocr.process_receipt(image_path, use_preprocessing=False)
            enhanced_time = time.time() - start_time
            
            if enhanced_result:
                print(f"  Vendor: {enhanced_result.get('vendor', 'N/A')}")
                print(f"  Date: {enhanced_result.get('issue_date', 'N/A')}")
                print(f"  Total: ¥{enhanced_result.get('total', 0):,.0f}")
                print(f"  Confidence: {enhanced_result.get('confidence_score', 0):.2f}")
                print(f"  Time: {enhanced_time:.2f}s")
            else:
                print("  ❌ Failed to extract data")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # 3. 強化版OCR（前処理あり）
        print("\n🔥 Enhanced OCR (with preprocessing):")
        print("-" * 30)
        start_time = time.time()
        try:
            enhanced_pp_result = enhanced_ocr.process_receipt(image_path, use_preprocessing=True)
            enhanced_pp_time = time.time() - start_time
            
            if enhanced_pp_result:
                print(f"  Vendor: {enhanced_pp_result.get('vendor', 'N/A')}")
                print(f"  Date: {enhanced_pp_result.get('issue_date', 'N/A')}")
                print(f"  Total: ¥{enhanced_pp_result.get('total', 0):,.0f}")
                print(f"  Confidence: {enhanced_pp_result.get('confidence_score', 0):.2f}")
                print(f"  Time: {enhanced_pp_time:.2f}s")
                
                # 詳細情報
                if enhanced_pp_result.get('line_items'):
                    print(f"  Items: {len(enhanced_pp_result['line_items'])} items detected")
                if enhanced_pp_result.get('address'):
                    print(f"  Address: {enhanced_pp_result['address'][:30]}...")
                if enhanced_pp_result.get('phone'):
                    print(f"  Phone: {enhanced_pp_result['phone']}")
            else:
                print("  ❌ Failed to extract data")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # 4. 複数フレーム統合テスト
    if len(test_images) >= 3:
        print(f"\n{'='*40}")
        print("Testing Multiple Frame Integration")
        print("="*40)
        
        start_time = time.time()
        try:
            multi_result = enhanced_ocr.process_multiple_frames(test_images[:5])
            multi_time = time.time() - start_time
            
            if multi_result:
                print(f"  Vendor: {multi_result.get('vendor', 'N/A')}")
                print(f"  Date: {multi_result.get('issue_date', 'N/A')}")
                print(f"  Total: ¥{multi_result.get('total', 0):,.0f}")
                print(f"  Confidence: {multi_result.get('confidence_score', 0):.2f}")
                print(f"  Time: {multi_time:.2f}s")
            else:
                print("  ❌ Failed to extract data")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    # .envファイルを読み込み
    from dotenv import load_dotenv
    load_dotenv()
    
    # OpenCVが必要
    try:
        import cv2
    except ImportError:
        print("Installing opencv-python...")
        os.system("pip install opencv-python")
    
    test_enhanced_ocr()