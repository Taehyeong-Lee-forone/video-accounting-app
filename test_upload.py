#!/usr/bin/env python3
"""テストビデオアップロードスクリプト"""
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import tempfile
import subprocess
import json

def create_test_receipt_image():
    """テスト用レシートイメージ生成"""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # レシート内容
    text = """
    ========== レシート ==========
    
    店舗名: テストカフェ
    発行日: 2025-02-07
    
    -------------------------
    
    アメリカーノ        5,000円
    サンドイッチ          8,000円
    
    -------------------------
    
    小計:            13,000円
    消費税(10%):      1,300円
    合計:            14,300円
    
    支払方法: クレジットカード
    
    =============================
    """
    
    # テキスト描画（デフォルトフォント使用）
    draw.text((50, 30), text, fill='black')
    
    # 一時ファイルで保存
    temp_path = "/tmp/test_receipt.png"
    img.save(temp_path)
    return temp_path

def create_test_video(image_path):
    """イメージからテストビデオ生成 (ffmpeg使用)"""
    video_path = "/tmp/test_receipt.mp4"
    
    # ffmpegでイメージを5秒ビデオに変換
    cmd = [
        'ffmpeg', '-y',
        '-loop', '1',
        '-i', image_path,
        '-c:v', 'libx264',
        '-t', '5',
        '-pix_fmt', 'yuv420p',
        video_path
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    return video_path

def upload_video(video_path):
    """ビデオをAPIでアップロード"""
    url = "http://localhost:8000/api/videos/"
    
    with open(video_path, 'rb') as f:
        files = {'file': ('test_receipt.mp4', f, 'video/mp4')}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ アップロード成功!")
        print(f"   Video ID: {result['id']}")
        print(f"   Status: {result['status']}")
        print(f"   Filename: {result['filename']}")
        return result['id']
    else:
        print(f"❌ アップロード失敗: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def check_status(video_id):
    """ビデオ処理状態確認"""
    url = f"http://localhost:8000/api/videos/{video_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        video = response.json()
        print(f"\n📊 処理状態:")
        print(f"   Status: {video['status']}")
        print(f"   Progress: {video.get('progress', 0)}%")
        print(f"   Message: {video.get('progress_message', '')}")
        if video.get('error_message'):
            print(f"   Error: {video['error_message']}")
        return video
    else:
        print(f"❌ 状態確認失敗: {response.status_code}")
        return None

def main():
    print("🎬 テストビデオアップロード開始...")
    
    try:
        # 1. テストレシートイメージ生成
        print("1️⃣ レシートイメージ生成中...")
        image_path = create_test_receipt_image()
        print(f"   ✅ イメージ生成: {image_path}")
        
        # 2. ビデオ生成
        print("2️⃣ ビデオ生成中...")
        video_path = create_test_video(image_path)
        print(f"   ✅ ビデオ生成: {video_path}")
        
        # 3. アップロード
        print("3️⃣ ビデオアップロード中...")
        video_id = upload_video(video_path)
        
        if video_id:
            # 4. 状態確認
            import time
            for i in range(30):  # 最大30秒待機
                time.sleep(2)
                video = check_status(video_id)
                if video and video['status'] in ['DONE', 'FAILED']:
                    break
            
            # 5. 最終結果確認
            if video and video['status'] == 'DONE':
                print("\n✅ ビデオ処理完了!")
                
                # レシートデータ確認
                receipts_url = f"http://localhost:8000/api/receipts/?video_id={video_id}"
                receipts_response = requests.get(receipts_url)
                if receipts_response.status_code == 200:
                    receipts = receipts_response.json()
                    if receipts:
                        print("\n📋 抽出されたレシートデータ:")
                        receipt = receipts[0]
                        print(f"   店舗名: {receipt.get('vendor')}")
                        print(f"   発行日: {receipt.get('issue_date')}")
                        print(f"   合計: {receipt.get('total')}円")
                        print(f"   支払方法: {receipt.get('payment_method')}")
            elif video and video['status'] == 'FAILED':
                print(f"\n❌ ビデオ処理失敗: {video.get('error_message')}")
            else:
                print("\n⏱️ 処理時間超過")
        
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()