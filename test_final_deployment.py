#!/usr/bin/env python3
"""
最終デプロイメントテスト
"""
import requests
import json
import time

BASE_URL = "https://video-accounting-app.onrender.com"

def test_health():
    """ヘルスチェック"""
    print("1. ヘルスチェック...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("✅ ヘルスチェック成功:", response.json())
    else:
        print("❌ ヘルスチェック失敗:", response.status_code)
    return response.status_code == 200

def test_upload_video():
    """ビデオアップロードテスト"""
    print("\n2. ビデオアップロードテスト...")
    
    # テスト用ビデオファイル確認
    video_path = "uploads/videos/1753309926185.mp4"
    try:
        with open(video_path, 'rb') as f:
            files = {'file': ('test_video.mp4', f, 'video/mp4')}
            response = requests.post(f"{BASE_URL}/videos/upload", files=files)
            
            if response.status_code == 200:
                video_data = response.json()
                print("✅ アップロード成功:")
                print(f"   - Video ID: {video_data.get('id')}")
                print(f"   - Status: {video_data.get('status')}")
                return video_data.get('id')
            else:
                print("❌ アップロード失敗:", response.status_code)
                print("   Response:", response.text)
                return None
    except FileNotFoundError:
        print("⚠️ テストビデオファイルが見つかりません:", video_path)
        return None
    except Exception as e:
        print("❌ エラー:", str(e))
        return None

def test_video_processing(video_id):
    """ビデオ処理状態確認"""
    if not video_id:
        return False
    
    print(f"\n3. ビデオ処理状態確認 (ID: {video_id})...")
    
    # 最大2分待機
    max_wait = 120
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{BASE_URL}/videos/{video_id}")
            if response.status_code == 200:
                video_data = response.json()
                status = video_data.get('status')
                receipts_count = len(video_data.get('receipts', []))
                
                print(f"   Status: {status}, Receipts: {receipts_count}")
                
                if status == 'completed':
                    print("✅ 処理完了!")
                    print(f"   - 検出された領収書: {receipts_count}枚")
                    return True
                elif status == 'failed':
                    print("❌ 処理失敗")
                    return False
            else:
                print(f"❌ ステータス確認失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ エラー: {str(e)}")
            return False
        
        time.sleep(5)
    
    print("⏱️ タイムアウト - 処理が完了しませんでした")
    return False

def test_api_endpoints():
    """主要APIエンドポイントテスト"""
    print("\n4. APIエンドポイントテスト...")
    
    endpoints = [
        ("/videos", "GET", "ビデオリスト"),
        ("/journals", "GET", "仕訳リスト"),
        ("/masters/accounts", "GET", "勘定科目マスター"),
    ]
    
    all_success = True
    for endpoint, method, description in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            
            if response.status_code in [200, 201]:
                print(f"✅ {description}: OK")
            else:
                print(f"❌ {description}: {response.status_code}")
                all_success = False
        except Exception as e:
            print(f"❌ {description}: エラー - {str(e)}")
            all_success = False
    
    return all_success

if __name__ == "__main__":
    print("="*50)
    print("最終デプロイメントテスト開始")
    print(f"サーバー: {BASE_URL}")
    print("="*50)
    
    # ヘルスチェック
    if not test_health():
        print("\n❌ サーバーが応答していません")
        exit(1)
    
    # ビデオアップロード
    video_id = test_upload_video()
    
    # ビデオ処理確認
    if video_id:
        test_video_processing(video_id)
    
    # APIエンドポイントテスト
    test_api_endpoints()
    
    print("\n" + "="*50)
    print("テスト完了")
    print("="*50)