#!/usr/bin/env python3
"""領収書データの詳細確認"""

import os
import requests
import json

# APIベースURLを環境変数から取得
API_URL = os.getenv("API_URL", "http://localhost:5001")

# 最新の動画を取得
videos = requests.get(f"{API_URL}/videos", timeout=3).json()
done = [v for v in videos if v.get('status') == 'done']

if done:
    latest = done[0]
    print(f"動画ID: {latest['id']}")
    
    # 詳細取得
    detail = requests.get(f"{API_URL}/videos/{latest['id']}", timeout=3).json()
    receipts = detail.get('receipts', [])
    
    print(f"\n全領収書データ ({len(receipts)}件):")
    for i, r in enumerate(receipts, 1):
        best_frame = r.get('best_frame', {})
        time_ms = best_frame.get('time_ms') if best_frame else None
        
        print(f"\n領収書 {i}:")
        print(f"  ID: {r.get('id')}")
        print(f"  店舗: {r.get('vendor', 'N/A')}")
        print(f"  金額: ¥{r.get('total', 0):,}")
        print(f"  best_frame_id: {r.get('best_frame_id')}")
        print(f"  best_frame: {best_frame}")
        print(f"  time_ms: {time_ms} ms")
        print(f"  時間: {time_ms/1000 if time_ms is not None else 'None'} 秒")
        
        if time_ms == 0:
            print("  ⚠️ 注意: time_msが0です！")
        elif time_ms is None:
            print("  ❌ エラー: time_msがありません！")