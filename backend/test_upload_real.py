#!/usr/bin/env python3
"""
実際のビデオファイルアップロードテスト
"""
import requests
import os
import time

# 配置された本番サーバー
BASE_URL = "https://video-accounting-app.onrender.com"

def test_real_upload():
    """実際のビデオファイルをアップロード"""
    print("="*50)
    print("実ビデオアップロードテスト - 修正後")
    print("="*50)
    
    # ログイン
    login_response = requests.post(
        f"{BASE_URL}/auth/login",  # /api なし
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ ログイン失敗: {login_response.status_code}")
        print(f"   Response: {login_response.text[:200]}")
        return
    
    token = login_response.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ ログイン成功")
    
    # 実際のビデオファイル
    video_file = "uploads/videos/1753309926185.mp4"
    
    if not os.path.exists(video_file):
        print(f"❌ ビデオファイルが見つかりません: {video_file}")
        return
    
    print(f"📹 アップロードファイル: {video_file}")
    print(f"   サイズ: {os.path.getsize(video_file) / 1024 / 1024:.2f} MB")
    
    # タイムスタンプ付きのファイル名
    timestamp = int(time.time())
    filename = f"test_{timestamp}.mp4"
    
    # アップロード
    print("\n⏳ アップロード中...")
    with open(video_file, 'rb') as f:
        files = {'file': (filename, f, 'video/mp4')}
        response = requests.post(
            f"{BASE_URL}/videos/",  # 正しいエンドポイント (/api なし)
            headers=headers,
            files=files,
            timeout=60  # 60秒タイムアウト
        )
    
    print(f"\n応答ステータス: {response.status_code}")
    
    if response.status_code == 200:
        video_data = response.json()
        video_id = video_data['id']
        print(f"✅ アップロード成功!")
        print(f"   Video ID: {video_id}")
        print(f"   ファイル名: {video_data.get('original_filename')}")
        print(f"   ステータス: {video_data.get('status')}")
        
        # 処理状況をモニタリング（30秒間）
        print("\n⏱️ 処理状況モニタリング (30秒間)...")
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < 30:
            detail_response = requests.get(
                f"{BASE_URL}/videos/{video_id}",  # /api なし
                headers=headers
            )
            
            if detail_response.status_code == 200:
                detail = detail_response.json()
                current_status = detail['status']
                progress = detail.get('progress', 0)
                message = detail.get('progress_message', '')
                
                # ステータスが変わったときのみ表示
                if current_status != last_status or progress > 0:
                    print(f"\r[{int(time.time() - start_time):2d}秒] "
                          f"Status: {current_status:12s} | "
                          f"Progress: {progress:3d}% | "
                          f"Message: {message[:40]:40s}", end="")
                    last_status = current_status
                
                # 処理完了または失敗したら終了
                if current_status in ['done', 'error']:
                    print(f"\n\n🏁 処理終了: {current_status}")
                    
                    if current_status == 'error':
                        print(f"❌ エラー: {detail.get('error_message', 'Unknown error')}")
                    else:
                        # 結果確認
                        frames = detail.get('frames', [])
                        receipts = detail.get('receipts', [])
                        print(f"✅ 処理成功!")
                        print(f"   フレーム数: {len(frames)}")
                        print(f"   領収書数: {len(receipts)}")
                        
                        if receipts:
                            print("\n検出された領収書:")
                            for receipt in receipts[:3]:  # 最初の3件を表示
                                print(f"   - {receipt.get('vendor')} ¥{receipt.get('total')}")
                    break
            
            time.sleep(2)  # 2秒ごとに確認
        else:
            print(f"\n\n⏱️ モニタリング終了 (30秒経過)")
            print(f"   最終ステータス: {last_status}")
    else:
        print(f"❌ アップロード失敗")
        print(f"   レスポンス: {response.text[:500]}")

if __name__ == "__main__":
    test_real_upload()