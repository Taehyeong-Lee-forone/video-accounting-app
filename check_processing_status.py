#!/usr/bin/env python3
"""
処理中のビデオステータス確認
"""
import requests
import time

BASE_URL = "https://video-accounting-app.onrender.com"

def check_processing_videos():
    """処理中のビデオを確認"""
    print("="*50)
    print("処理ステータス確認")
    print("="*50)
    
    # admin でログイン
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    
    if login_response.status_code != 200:
        print("❌ ログイン失敗")
        return
    
    token = login_response.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # ビデオリスト取得
    videos_response = requests.get(f"{BASE_URL}/videos", headers=headers)
    
    if videos_response.status_code == 200:
        videos = videos_response.json()
        
        print(f"\n総ビデオ数: {len(videos)}")
        
        for video in videos:
            print(f"\n📹 Video ID: {video.get('id')}")
            print(f"   ファイル: {video.get('original_filename', video.get('filename'))}")
            print(f"   ステータス: {video.get('status')}")
            print(f"   作成時刻: {video.get('created_at')}")
            
            # 詳細情報取得
            detail_response = requests.get(f"{BASE_URL}/videos/{video['id']}", headers=headers)
            if detail_response.status_code == 200:
                detail = detail_response.json()
                print(f"   フレーム数: {len(detail.get('frames', []))}")
                print(f"   領収書数: {len(detail.get('receipts', []))}")
                
                # エラーメッセージがあれば表示
                if detail.get('error_message'):
                    print(f"   ❌ エラー: {detail['error_message']}")
    else:
        print(f"❌ ビデオリスト取得失敗: {videos_response.status_code}")

def monitor_latest_video():
    """最新のビデオの処理状況をモニタリング"""
    print("\n" + "="*50)
    print("最新ビデオのリアルタイムモニタリング")
    print("="*50)
    
    # admin でログイン
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    
    if login_response.status_code != 200:
        return
    
    token = login_response.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # 最新のビデオを取得
    videos_response = requests.get(f"{BASE_URL}/videos", headers=headers)
    if videos_response.status_code == 200:
        videos = videos_response.json()
        if videos:
            latest_video = videos[0]  # 最新のビデオ
            video_id = latest_video['id']
            
            print(f"\n監視中: Video ID {video_id}")
            
            # 60秒間モニタリング
            start_time = time.time()
            while time.time() - start_time < 60:
                detail_response = requests.get(f"{BASE_URL}/videos/{video_id}", headers=headers)
                if detail_response.status_code == 200:
                    detail = detail_response.json()
                    print(f"\r⏱️ {int(time.time() - start_time)}秒 | "
                          f"Status: {detail['status']} | "
                          f"Frames: {len(detail.get('frames', []))} | "
                          f"Receipts: {len(detail.get('receipts', []))}", end="")
                    
                    if detail['status'] in ['completed', 'failed', 'error']:
                        print(f"\n\n✅ 処理完了: {detail['status']}")
                        break
                
                time.sleep(2)  # 2秒ごとに確認

if __name__ == "__main__":
    check_processing_videos()
    # monitor_latest_video()  # 必要に応じてコメントアウト解除