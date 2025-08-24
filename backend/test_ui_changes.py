#!/usr/bin/env python3
"""
UI変更のテストスクリプト
新しい「詳細表示」ボタンと領収書クリックの動作を確認
"""

import requests
import json

API_URL = "http://localhost:5001"

def test_get_videos():
    """動画リストを取得してレビューページの確認"""
    try:
        response = requests.get(f"{API_URL}/videos", timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"❌ API接続エラー: {e}")
        return None
        
    if response.status_code == 200:
        videos = response.json()
        print(f"✅ 動画リスト取得成功: {len(videos)}件の動画")
        
        # 最新の処理済み動画を確認
        done_videos = [v for v in videos if v.get('status') == 'DONE']
        if done_videos:
            latest = done_videos[0]
            print(f"\n📹 最新の処理済み動画:")
            print(f"  - ID: {latest['id']}")
            print(f"  - ファイル: {latest['filename']}")
            print(f"  - 作成日時: {latest['created_at']}")
            print(f"\n🔗 レビューページURL: http://localhost:3000/review/{latest['id']}")
            
            # 動画詳細から領収書データを確認
            try:
                detail_response = requests.get(f"{API_URL}/videos/{latest['id']}", timeout=5)
            except requests.exceptions.RequestException as e:
                print(f"❌ 詳細取得エラー: {e}")
                return latest['id']
                
            if detail_response.status_code == 200:
                detail = detail_response.json()
                receipts = detail.get('receipts', [])
                print(f"\n📋 領収書データ: {len(receipts)}件")
                
                if receipts:
                    print("\n領収書リスト:")
                    for i, receipt in enumerate(receipts[:3], 1):
                        print(f"  {i}. 店舗: {receipt.get('vendor', 'N/A')}")
                        print(f"     金額: ¥{receipt.get('total', 0):,}")
                        print(f"     フレーム: {receipt.get('best_frame', {}).get('time_ms', 0)}ms")
                    
                    print("\n✨ UI変更の確認ポイント:")
                    print("  1. 領収書をクリック → ビデオがそのフレームにシーク")
                    print("  2. 「詳細表示」ボタン → モーダルが開く")
                    print("  3. CSV出力ボタン → 既存の機能は維持")
            
            return latest['id']
    else:
        print(f"❌ 動画リスト取得失敗: {response.status_code}")
    
    return None

def main():
    print("=" * 60)
    print("UI変更テスト - 領収書分析レビュー画面")
    print("=" * 60)
    
    video_id = test_get_videos()
    
    if video_id:
        print("\n" + "=" * 60)
        print("📝 テスト手順:")
        print("=" * 60)
        print("1. ブラウザで上記URLを開く")
        print("2. 領収書をクリックして、ビデオがシークされることを確認")
        print("3. 「詳細表示」ボタンをクリックして、モーダルが開くことを確認")
        print("4. 領収書未選択時に「詳細表示」ボタンが無効になることを確認")
        print("\n✅ すべての機能が正常に動作すればテスト完了！")

if __name__ == "__main__":
    main()