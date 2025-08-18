#!/usr/bin/env python3
import os
import google.generativeai as genai
from PIL import Image
import json
import sys

# Configure Gemini
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key or gemini_api_key == "your-gemini-api-key-here":
    print("GEMINI_API_KEY not set")
    sys.exit(1)

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# Test with frame 20 (different frame)
frame_path = "uploads/frames/test_video_frame_000020.jpg"
if not os.path.exists(frame_path):
    print(f"Frame not found: {frame_path}")
    # Try to find any frame
    import glob
    frames = glob.glob("uploads/frames/*.jpg")
    if frames:
        frame_path = frames[0]
        print(f"Using frame: {frame_path}")
    else:
        print("No frames found")
        sys.exit(1)

image = Image.open(frame_path)

prompt = """あなたは日本の領収書/インボイスの読取りアシスタントです。
画像から全てのテキストを読み取り、以下のJSONを返してください（存在しないキーはnull）。
{
  "vendor": "...",
  "document_type": "領収書|請求書|レシート|見積書|その他",
  "issue_date": "日付文字列をそのまま（例: 令和6年12月25日, R6.12.25, 2024-12-25）",
  "currency": "JPY",
  "total": 0,
  "subtotal": 0,
  "tax": 0,
  "tax_rate": 0.10|0.08|0|null,
  "line_items": [{"name":"...", "qty":1, "unit_price":0, "amount":0}],
  "payment_method": "現金|クレジット|電子マネー|不明",
  "memo": "補足情報"
}
返答はJSONのみ。金額は数値として返してください。
日付は画像に表示されている通りの文字列をそのまま返してください（令和、平成、昭和などの元号も含めて）。
例: "令和6年12月25日", "R6/12/25", "平成31年4月30日", "2024-12-25" など
画像からテキストを直接読み取って認識してください。手書き数字も推定してください。

重要: document_typeは必ず5つの選択肢（領収書、請求書、レシート、見積書、その他）の中から1つだけを選んでください。
「請求書・領収書」のような複合的な表記は使用しないでください。最も適切な1つを選択してください。
"""

print("Sending request to Gemini...")
response = model.generate_content([image, prompt])

print(f"Raw response:\n{response.text}")

# Try to parse JSON
json_str = response.text.strip()
if json_str.startswith('```json'):
    json_str = json_str[7:]
if json_str.endswith('```'):
    json_str = json_str[:-3]

try:
    data = json.loads(json_str)
    print(f"\nParsed document_type: '{data.get('document_type')}'")
except Exception as e:
    print(f"Failed to parse JSON: {e}")