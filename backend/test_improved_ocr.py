#!/usr/bin/env python3
"""
改善版OCRテストスクリプト
店舗名（発行元）と日付の精度を向上
"""

import os
import sys
import json
import google.generativeai as genai
from PIL import Image
from pathlib import Path

# 改善版プロンプトをインポート
sys.path.append(str(Path(__file__).parent))
from services.improved_ocr_prompt import (
    get_improved_prompt,
    parse_vendor_from_ocr,
    extract_date_from_current_frame_only
)

def test_improved_ocr(image_path: str):
    """改善版OCRテスト"""
    
    # Gemini API設定
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("❌ GEMINI_API_KEY not set")
        return None
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 画像読み込み
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return None
    
    image = Image.open(image_path)
    
    # 改善版プロンプトを使用
    prompt = get_improved_prompt()
    
    print("=" * 60)
    print("改善版OCRテスト")
    print("=" * 60)
    print(f"画像: {image_path}")
    print("\n📤 Sending request to Gemini with improved prompt...")
    
    try:
        response = model.generate_content([image, prompt])
        
        # JSON解析
        json_str = response.text.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]
        
        data = json.loads(json_str)
        
        print("\n✅ OCR結果:")
        print("-" * 40)
        
        # 店舗名と宛名の区別
        print(f"🏪 発行元（店舗）: {data.get('vendor', 'N/A')}")
        if data.get('recipient'):
            print(f"📝 宛名: {data.get('recipient', 'N/A')}")
        
        # 日付
        print(f"📅 発行日: {data.get('issue_date', 'N/A')}")
        
        # 金額
        print(f"💰 総額: ¥{data.get('total', 0):,}")
        if data.get('subtotal'):
            print(f"   小計: ¥{data.get('subtotal', 0):,}")
        if data.get('tax'):
            print(f"   税額: ¥{data.get('tax', 0):,}")
        
        # 住所・電話（発行元の情報）
        if data.get('address'):
            print(f"📍 住所: {data.get('address')}")
        if data.get('phone'):
            print(f"📞 電話: {data.get('phone')}")
        
        # 商品明細
        if data.get('line_items'):
            print(f"\n📋 商品明細:")
            for item in data['line_items'][:3]:  # 最初の3件のみ表示
                print(f"   - {item.get('name')}: ¥{item.get('amount', 0):,}")
        
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}")
        print(f"Raw response: {response.text[:500]}")
        return None
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def compare_ocr_results(image_path: str):
    """
    従来版と改善版の比較
    """
    print("\n" + "=" * 60)
    print("従来版 vs 改善版 比較テスト")
    print("=" * 60)
    
    # 従来版プロンプト
    old_prompt = """あなたは日本の領収書/インボイスの読取りアシスタントです。
画像から全てのテキストを読み取り、以下のJSONを返してください（存在しないキーはnull）。
{
  "vendor": "...",
  "document_type": "領収書|請求書|レシート|見積書|その他",
  "issue_date": "日付文字列をそのまま",
  "total": 0,
  "subtotal": 0,
  "tax": 0
}
返答はJSONのみ。"""
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    image = Image.open(image_path)
    
    # 従来版実行
    print("\n【従来版】")
    try:
        response = model.generate_content([image, old_prompt])
        json_str = response.text.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:-3]
        old_data = json.loads(json_str)
        print(f"店舗: {old_data.get('vendor')}")
        print(f"日付: {old_data.get('issue_date')}")
    except:
        print("エラー")
        old_data = {}
    
    # 改善版実行
    print("\n【改善版】")
    new_data = test_improved_ocr(image_path)
    
    # 比較結果
    if old_data and new_data:
        print("\n" + "=" * 40)
        print("📊 比較結果")
        print("-" * 40)
        
        if old_data.get('vendor') != new_data.get('vendor'):
            print(f"店舗名の違い:")
            print(f"  従来: {old_data.get('vendor')}")
            print(f"  改善: {new_data.get('vendor')} ✨")
        
        if old_data.get('issue_date') != new_data.get('issue_date'):
            print(f"日付の違い:")
            print(f"  従来: {old_data.get('issue_date')}")
            print(f"  改善: {new_data.get('issue_date')} ✨")

def main():
    """メイン処理"""
    
    # テスト画像を探す
    test_images = [
        "uploads/frames/test_video_frame_000020.jpg",
        "backend/uploads/frames/test_video_frame_000020.jpg",
    ]
    
    # グロブパターンで検索
    import glob
    frame_files = glob.glob("uploads/frames/*.jpg") or glob.glob("backend/uploads/frames/*.jpg")
    if frame_files:
        test_images.extend(frame_files[:3])
    
    # 最初に見つかった画像でテスト
    for img_path in test_images:
        if os.path.exists(img_path):
            # 通常テスト
            result = test_improved_ocr(img_path)
            
            # 比較テスト（オプション）
            if '--compare' in sys.argv:
                compare_ocr_results(img_path)
            
            break
    else:
        print("❌ テスト画像が見つかりません")
        print("画像を指定してください: python test_improved_ocr.py <image_path>")

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        # コマンドライン引数で画像を指定
        test_improved_ocr(sys.argv[1])
    else:
        main()