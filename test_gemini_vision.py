#!/usr/bin/env python3
"""Gemini Vision API OCR テスト"""
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# 環境変数読み込み
load_dotenv('backend/.env')

# API キー設定
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key: {api_key[:10]}..." if api_key else "API Key not found")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # テスト画像作成（簡単な領収書のテキスト画像）
    from PIL import Image, ImageDraw, ImageFont
    
    # 白い背景の画像作成
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    # テキスト追加
    text = """
    RECEIPT
    
    Store: ABC Mart
    Date: 2025-08-16
    
    Item 1: Coffee    $5.00
    Item 2: Sandwich  $8.00
    
    Subtotal: $13.00
    Tax:      $1.30
    Total:    $14.30
    
    Thank you!
    """
    
    draw.text((20, 20), text, fill='black')
    img.save('/tmp/test_receipt.png')
    
    # Gemini Vision でOCR
    prompt = """
    この画像からテキストを読み取って、以下のJSON形式で返してください：
    {
        "vendor": "店名",
        "issue_date": "YYYY-MM-DD",
        "total": 合計金額（数値）,
        "items": ["商品リスト"]
    }
    JSONのみ返答してください。
    """
    
    try:
        image = Image.open('/tmp/test_receipt.png')
        response = model.generate_content([image, prompt])
        print("\n=== Gemini Vision OCR結果 ===")
        print(response.text)
        print("\n✅ Gemini Vision APIでOCRと分析が同時にできます！")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
else:
    print("\n❌ API キーが設定されていません")