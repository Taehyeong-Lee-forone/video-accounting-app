#!/usr/bin/env python3
"""領収書クリックのシーク機能テスト"""

import requests
import json

# 最新の動画を取得
videos = requests.get("http://localhost:5001/videos", timeout=3).json()
done = [v for v in videos if v.get('status') == 'done']

if done:
    latest = done[0]
    print(f"✅ テスト対象動画: ID={latest['id']}")
    print(f"📹 URL: http://localhost:3000/review/{latest['id']}")
    
    # 詳細取得
    detail = requests.get(f"http://localhost:5001/videos/{latest['id']}", timeout=3).json()
    receipts = detail.get('receipts', [])
    
    print(f"\n📋 領収書リスト ({len(receipts)}件):")
    for i, r in enumerate(receipts[:5], 1):
        time_ms = r.get('best_frame', {}).get('time_ms', 0)
        time_sec = time_ms / 1000 if time_ms else 0
        print(f"  {i}. {r.get('vendor', 'N/A'):20} @ {time_sec:6.1f}秒 ({time_ms}ms)")
    
    print("\n🔧 修正内容:")
    print("  ✅ videoRef を CustomVideoPlayer に渡すように修正")
    print("  ✅ playerRef.current を videoRef.current に変更")
    print("  ✅ ReactPlayer の seekTo を HTML5 video の currentTime に変更")
    
    print("\n📝 テスト手順:")
    print("  1. ブラウザで上記URLを開く")
    print("  2. 開発者ツールのコンソールを開く")
    print("  3. 領収書をクリック")
    print("  4. コンソールに 'Attempting to seek to: X seconds' が表示される")
    print("  5. ビデオがその時間にジャンプする")
    
else:
    print("❌ 処理済み動画がありません")