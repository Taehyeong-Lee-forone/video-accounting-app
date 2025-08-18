#!/usr/bin/env python3
"""Gemini API テスト"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# 環境変数読み込み
load_dotenv('backend/.env')

# API キー設定
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key: {api_key[:10]}..." if api_key else "API Key not found")

if api_key and api_key != "your-gemini-api-key-here":
    genai.configure(api_key=api_key)
    
    # モデル初期化
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # テキストのみで簡単なテスト
    prompt = "1+1は?"
    
    try:
        response = model.generate_content(prompt)
        print(f"\n質問: {prompt}")
        print(f"回答: {response.text}")
        print("\n✅ Gemini API は正常に動作しています!")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
else:
    print("\n❌ API キーが設定されていません")