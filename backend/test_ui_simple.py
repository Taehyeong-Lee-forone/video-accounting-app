#!/usr/bin/env python3
"""簡単なUIテスト"""

import requests
import json

# 動画リスト取得
videos = requests.get("http://localhost:5001/videos", timeout=3).json()
print(f"✅ 動画数: {len(videos)}")

# 最新の処理済み動画
done = [v for v in videos if v.get('status') == 'done']
if done:
    latest = done[0]
    print(f"\n📹 最新動画: ID={latest['id']}, ファイル={latest['filename']}")
    print(f"🔗 レビューページ: http://localhost:3000/review/{latest['id']}")
    
    # 詳細取得
    detail = requests.get(f"http://localhost:5001/videos/{latest['id']}", timeout=3).json()
    receipts = detail.get('receipts', [])
    
    print(f"\n📋 領収書: {len(receipts)}件")
    for i, r in enumerate(receipts[:3], 1):
        print(f"  {i}. {r.get('vendor', 'N/A')} - ¥{r.get('total', 0):,}")
    
    print("\n✨ UI確認ポイント:")
    print("  1. 領収書クリック → ビデオシーク")
    print("  2. 「詳細表示」ボタン → モーダル表示")
    print("  3. 領収書未選択時 → ボタン無効")