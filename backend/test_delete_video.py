#!/usr/bin/env python3
"""
ビデオ削除テスト
"""
import requests

BASE_URL = "https://video-accounting-app.onrender.com"

def test_delete_video():
    """ビデオ削除テスト"""
    print("="*50)
    print("ビデオ削除テスト")
    print("="*50)
    
    # ログイン
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
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
    
    # ビデオリスト取得
    videos_response = requests.get(f"{BASE_URL}/videos", headers=headers)
    
    if videos_response.status_code == 200:
        videos = videos_response.json()
        print(f"\n📹 ビデオ総数: {len(videos)}")
        
        if videos:
            # 最後のビデオを削除対象にする
            target_video = videos[-1]
            video_id = target_video['id']
            print(f"\n削除対象: Video ID {video_id}")
            print(f"   ファイル: {target_video.get('original_filename', 'N/A')}")
            print(f"   ステータス: {target_video.get('status')}")
            
            # 削除実行
            print(f"\n⚠️ Video ID {video_id} を削除中...")
            delete_response = requests.delete(
                f"{BASE_URL}/videos/{video_id}",
                headers=headers
            )
            
            print(f"\n削除レスポンス: {delete_response.status_code}")
            
            if delete_response.status_code == 200:
                print("✅ 削除成功!")
                print(f"   Response: {delete_response.json()}")
            else:
                print(f"❌ 削除失敗!")
                print(f"   Response: {delete_response.text[:500]}")
                
                # エラーの詳細を表示
                try:
                    error_detail = delete_response.json()
                    print(f"\n📌 エラー詳細:")
                    print(f"   {error_detail}")
                except:
                    pass
        else:
            print("削除するビデオがありません")
    else:
        print(f"❌ ビデオリスト取得失敗: {videos_response.status_code}")

if __name__ == "__main__":
    test_delete_video()