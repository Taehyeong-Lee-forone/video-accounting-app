#!/usr/bin/env python3
"""
プロダクション環境でのメール送信テスト
"""
import requests
import json
import time

PROD_URL = "https://video-accounting-app.onrender.com"
TEST_EMAIL = "ritehyon@gmail.com"

def test_password_reset():
    """パスワードリセットメールのテスト"""
    
    print("=" * 50)
    print(f"📧 メール送信テスト開始")
    print(f"対象メール: {TEST_EMAIL}")
    print(f"環境: プロダクション ({PROD_URL})")
    print("=" * 50)
    
    # 1. パスワードリセットリクエスト送信
    print("\n1️⃣ パスワードリセットリクエスト送信中...")
    response = requests.post(
        f"{PROD_URL}/api/auth/forgot-password",
        json={"email": TEST_EMAIL},
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   ステータスコード: {response.status_code}")
    
    try:
        result = response.json()
        print(f"   レスポンス: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            print("   ✅ リクエスト成功！")
            print(f"   📮 {TEST_EMAIL} のメールボックスを確認してください")
            print("   📝 件名: 【動画会計アプリ】パスワードリセットのご案内")
        else:
            print(f"   ❌ エラー: {result.get('detail', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ❌ パースエラー: {e}")
        print(f"   生レスポンス: {response.text}")
    
    return response.status_code == 200

def check_server_logs():
    """サーバーログを確認（可能な場合）"""
    print("\n2️⃣ サーバー状態確認中...")
    
    # DB情報エンドポイントで環境変数の状態を確認
    response = requests.get(f"{PROD_URL}/db-info")
    if response.status_code == 200:
        info = response.json()
        print(f"   データベース: {info.get('database_type')}")
        print(f"   Render環境: {info.get('render_env')}")
        print(f"   統計: {info.get('statistics')}")

def main():
    """メインテスト実行"""
    
    # メール送信テスト
    success = test_password_reset()
    
    # サーバー状態確認
    check_server_logs()
    
    # 結果サマリー
    print("\n" + "=" * 50)
    if success:
        print("🎉 テスト完了！")
        print(f"📧 {TEST_EMAIL} のメールボックスを確認してください")
        print("⏰ メールが届くまで1-2分かかる場合があります")
    else:
        print("❌ テスト失敗")
        print("📝 Renderのログを確認してください:")
        print("   https://dashboard.render.com/")
    print("=" * 50)

if __name__ == "__main__":
    main()
