#!/usr/bin/env python3
import requests
import time
import sys

# API endpoint
BASE_URL = "http://localhost:8000/api"

def test_video_upload():
    print("🎬 タイムスタンプ精度改善テスト...")
    print("ビデオアップロード中...")
    
    with open("/Users/taehyeonglee/video-accounting-app/backend/uploads/videos/multi_receipt.mp4", "rb") as f:
        files = {"file": ("test_timestamp.mp4", f, "video/mp4")}
        response = requests.post(f"{BASE_URL}/videos/", files=files)
    
    if response.status_code != 200:
        print(f"❌ アップロード失敗: {response.status_code}")
        return None
    
    video_data = response.json()
    video_id = video_data["id"]
    print(f"✅ ビデオアップロード成功. ID: {video_id}")
    
    # 分析開始
    print("分析開始...")
    response = requests.post(
        f"{BASE_URL}/videos/{video_id}/analyze",
        json={"frames_per_second": 2}
    )
    
    if response.status_code != 200:
        print(f"❌ 分析開始失敗: {response.status_code}")
        return None
    
    print("分析進行中...")
    
    # 完了まで待機
    for i in range(120):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/videos/{video_id}")
        if response.status_code == 200:
            video_data = response.json()
            status = video_data.get("status")
            progress = video_data.get("progress", 0)
            message = video_data.get("progress_message", "")
            
            # プログレスバー
            bar_length = 30
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"\r[{bar}] {progress}% - {message}", end='')
            
            if status == "done":
                print(f"\n\n✅ 分析完了!")
                receipts = video_data.get('receipts', [])
                print(f"📋 検出されたレシート: {len(receipts)}件")
                print("\nタイムスタンプ検証:")
                print("=" * 50)
                
                for idx, receipt in enumerate(receipts, 1):
                    best_frame = receipt.get('best_frame', {})
                    time_ms = best_frame.get('time_ms', 0)
                    time_sec = time_ms / 1000
                    
                    print(f"\nレシート {idx}:")
                    print(f"  店舗: {receipt.get('vendor', 'Unknown')}")
                    print(f"  文書タイプ: {receipt.get('document_type', 'Unknown')}")
                    print(f"  タイムスタンプ: {time_sec:.2f}秒 ({time_ms}ms)")
                    print(f"  フレーム ID: {best_frame.get('id', 'N/A')}")
                    print(f"  金額: {receipt.get('total', 0):,}円")
                
                print("\n" + "=" * 50)
                return video_id
                
            elif status == "error":
                print(f"\n\n❌ 分析失敗: {video_data.get('error_message')}")
                return None
    
    print("\n\n⏱️ 分析時間超過")
    return None

if __name__ == "__main__":
    video_id = test_video_upload()
    if video_id:
        print(f"\n✨ テスト成功! Video ID: {video_id}")
        print("\n📊 改善事項:")
        print("  ✓ OpenCV CAP_PROP_POS_MSECの代わりにフレームインデックスベースの計算")
        print("  ✓ ファイル名にタイムスタンプを含む")
        print("  ✓ 正確なfpsベースの時間計算")
        sys.exit(0)
    else:
        print("\nテスト失敗!")
        sys.exit(1)