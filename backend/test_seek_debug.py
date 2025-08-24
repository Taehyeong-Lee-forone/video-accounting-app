#!/usr/bin/env python3
"""シーク機能のデバッグ情報"""

import requests

# 最新の動画を取得
videos = requests.get("http://localhost:5001/videos", timeout=3).json()
done = [v for v in videos if v.get('status') == 'done']

if done:
    latest = done[0]
    print("=" * 60)
    print("📹 シーク機能デバッグガイド")
    print("=" * 60)
    print(f"\nテスト対象: http://localhost:3000/review/{latest['id']}")
    
    # 詳細取得
    detail = requests.get(f"http://localhost:5001/videos/{latest['id']}", timeout=3).json()
    receipts = detail.get('receipts', [])[:5]
    
    print("\n🔍 確認手順:")
    print("1. ブラウザで上記URLを開く")
    print("2. 開発者ツールのコンソールを開く (F12)")
    print("3. 以下の領収書を順番にクリック:")
    print()
    
    for i, r in enumerate(receipts, 1):
        time_ms = r.get('best_frame', {}).get('time_ms', 0) if r.get('best_frame') else 0
        time_sec = time_ms / 1000
        print(f"  領収書{i}: {r.get('vendor', 'N/A'):15} → {time_sec:5.1f}秒にジャンプすべき")
    
    print("\n📝 コンソールで確認すべきログ:")
    print("  - 'Clicked receipt data:' - クリックした領収書のデータ")
    print("  - 'Receipt best_frame:' - best_frameオブジェクト")
    print("  - 'time_ms:' - ミリ秒単位の時間")
    print("  - 'Attempting to seek to:' - シーク先の秒数")
    print("  - 'Before seek - video properties:' - ビデオの状態")
    print("  - 'Immediately after seek:' - シーク直後の位置")
    print("  - 'After 100ms delay:' - 遅延後の位置")
    
    print("\n⚠️ 問題の診断:")
    print("  • すべて0秒になる → videoRef接続の問題")
    print("  • ログが出ない → クリックハンドラーの問題")
    print("  • time_msがundefined → データ構造の問題")
    print("  • readyStateが低い → ビデオ読み込みの問題")
    
else:
    print("❌ 処理済み動画がありません")