#!/usr/bin/env python3
"""
AI Service テストスクリプト（Gemini/OpenAI切り替えテスト）
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from services.ai_service import AIService

def test_ai_service():
    """AI Serviceのテスト"""
    
    print("=" * 60)
    print("AI Service Test")
    print("=" * 60)
    
    # 現在の設定を表示
    provider = os.getenv("AI_PROVIDER", "gemini")
    print(f"Current AI Provider: {provider}")
    print(f"OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY'))}")
    print(f"GEMINI_API_KEY set: {bool(os.getenv('GEMINI_API_KEY'))}")
    print()
    
    # AIサービスを初期化
    ai_service = AIService()
    
    # プロバイダー情報を表示
    info = ai_service.get_provider_info()
    print("Provider Info:")
    print(f"  Provider: {info['provider']}")
    print(f"  Model: {info['model']}")
    print(f"  Available: {info['available']}")
    print()
    
    # テスト用OCRテキスト
    test_text = """
太郎商店様
船橋市市場1-1-1
TEL: 047-123-4567

6年11月26日

商品A  1,000円
商品B  2,000円
商品C  2,616円

小計    5,616円
消費税    561円
合計    6,177円

現金でお支払い
"""
    
    print("Testing with sample OCR text...")
    print("-" * 40)
    
    # AI処理を実行
    result = ai_service.process_receipt(test_text)
    
    if result:
        print("✅ AI Processing Successful!")
        print("\nExtracted Information:")
        print(f"  Vendor: {result.get('vendor', 'N/A')}")
        print(f"  Date: {result.get('issue_date', 'N/A')}")
        print(f"  Total: ¥{result.get('total', 0):,.0f}")
        print(f"  Tax: ¥{result.get('tax', 0):,.0f}")
        print(f"  Document Type: {result.get('document_type', 'N/A')}")
        
        # 日付の検証
        if result.get('issue_date'):
            if '令和6年11月26日' in str(result['issue_date']) or '6年11月26日' in str(result['issue_date']):
                print("\n✅ Date extraction correct!")
            else:
                print(f"\n⚠️ Date might be incorrect: {result['issue_date']}")
        
    else:
        print("❌ AI Processing Failed")
    
    print("\n" + "=" * 60)
    
    # プロバイダー切り替えのヒント
    if provider == "gemini":
        print("\nTo switch to OpenAI GPT-4:")
        print("1. Set OPENAI_API_KEY in .env file")
        print("2. Set AI_PROVIDER=openai in .env file")
        print("3. Run: pip install openai")
    else:
        print("\nTo switch back to Gemini:")
        print("1. Set AI_PROVIDER=gemini in .env file")

if __name__ == "__main__":
    # .envファイルを読み込み
    from dotenv import load_dotenv
    load_dotenv()
    
    test_ai_service()