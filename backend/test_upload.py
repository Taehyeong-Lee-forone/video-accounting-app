#!/usr/bin/env python3
import requests
import sys
import os

# API URL
url = "https://video-accounting-app.onrender.com/videos/"

# テストファイルパス
test_file = "/Users/taehyeonglee/video-accounting-app/backend/uploads/videos/1753309926185.mp4"

if not os.path.exists(test_file):
    print(f"テストファイルが見つかりません: {test_file}")
    sys.exit(1)

print(f"ファイルサイズ: {os.path.getsize(test_file) / 1024 / 1024:.2f} MB")

# ファイルアップロード
with open(test_file, 'rb') as f:
    files = {'file': ('test_video.mp4', f, 'video/mp4')}
    
    print("アップロード中...")
    try:
        response = requests.post(url, files=files, timeout=30)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.text}")
        
        if response.status_code == 200:
            print("✅ アップロード成功!")
        else:
            print("❌ アップロード失敗")
            
    except Exception as e:
        print(f"エラー: {e}")
