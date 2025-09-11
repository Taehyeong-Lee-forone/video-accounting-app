#!/usr/bin/env python3
"""
GPT-4V統合テストスクリプト
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

def test_gpt4v_service():
    """GPT-4Vサービスのテスト"""
    
    print("=" * 60)
    print("🧪 GPT-4V統合テスト")
    print("=" * 60)
    
    # 1. 環境変数チェック
    print("\n📋 環境変数チェック:")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        print("❌ OPENAI_API_KEY が設定されていません")
        print("\n👉 設定方法:")
        print("1. https://platform.openai.com/api-keys でAPIキーを取得")
        print("2. .envファイルに追加: OPENAI_API_KEY=sk-xxxxx")
        return False
    else:
        print(f"✅ OPENAI_API_KEY: {api_key[:7]}...{api_key[-4:]}")
    
    # 2. GPT-4Vサービス初期化
    print("\n📦 GPT-4Vサービス初期化:")
    try:
        from services.gpt4v_service import GPT4VisionService
        service = GPT4VisionService()
        print("✅ サービス初期化成功")
    except Exception as e:
        print(f"❌ 初期化失敗: {e}")
        return False
    
    # 3. テスト画像で実行
    print("\n🖼️ テスト画像で領収書抽出:")
    
    # テスト画像を探す
    test_images = [
        "uploads/frames/frame_0000.jpg",
        "uploads/frames/frame_0001.jpg",
        "uploads/frames/frame_26.jpg",
        "uploads/frames/frame_20.jpg",
    ]
    
    test_image = None
    for img_path in test_images:
        if Path(img_path).exists():
            test_image = img_path
            break
    
    if not test_image:
        print("⚠️ テスト画像が見つかりません")
        print("動画をアップロードしてフレームを生成してください")
        return False
    
    print(f"📄 使用画像: {test_image}")
    
    # 4. 領収書抽出実行
    print("\n🔍 GPT-4Vで領収書データ抽出中...")
    try:
        result = service.extract_receipt(test_image)
        
        if result:
            print("✅ 抽出成功!")
            print("\n📊 抽出結果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 主要フィールドの確認
            print("\n📝 主要データ:")
            print(f"  • 店舗名: {result.get('vendor', '不明')}")
            print(f"  • 日付: {result.get('date', '不明')}")
            print(f"  • 合計: ¥{result.get('total', 0):,.0f}")
            print(f"  • 商品数: {len(result.get('items', []))}")
            
            return True
        else:
            print("❌ 領収書データを抽出できませんでした")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def compare_with_old_system():
    """旧システムとの比較"""
    print("\n" + "=" * 60)
    print("📊 旧システムとの比較")
    print("=" * 60)
    
    print("\n🔴 旧システム (Cloud Vision + Gemini):")
    print("  • 処理ステップ: 2段階")
    print("  • コスト: $0.0018/画像")
    print("  • 精度: 中程度")
    print("  • コード: 1000行以上")
    
    print("\n🟢 新システム (GPT-4V統合):")
    print("  • 処理ステップ: 1段階")
    print("  • コスト: $0.01-0.03/画像")
    print("  • 精度: 高い")
    print("  • コード: 300行")
    
    print("\n💡 推奨:")
    print("  • 月間100-300枚: GPT-4V推奨")
    print("  • 月間1000枚以上: ハイブリッド検討")

def setup_instructions():
    """セットアップ手順"""
    print("\n" + "=" * 60)
    print("🚀 GPT-4V移行手順")
    print("=" * 60)
    
    print("\n1️⃣ OpenAI APIキー取得:")
    print("   https://platform.openai.com/api-keys")
    
    print("\n2️⃣ .envファイル更新:")
    print("   OPENAI_API_KEY=sk-xxxxxxxxxxxxx")
    print("   VISION_PROVIDER=gpt4v")
    
    print("\n3️⃣ Render環境変数追加:")
    print("   Dashboard → Environment → Add Environment Variable")
    print("   • OPENAI_API_KEY = [APIキー]")
    print("   • VISION_PROVIDER = gpt4v")
    
    print("\n4️⃣ デプロイ:")
    print("   git add -A")
    print("   git commit -m 'feat: GPT-4V統合'")
    print("   git push origin main")
    
    print("\n5️⃣ 旧設定の削除:")
    print("   • GEMINI_API_KEY (不要)")
    print("   • GOOGLE_APPLICATION_CREDENTIALS (不要)")
    print("   • AI_PROVIDER (不要)")

if __name__ == "__main__":
    print("\n🎯 GPT-4V統合テスト開始\n")
    
    # メインテスト実行
    success = test_gpt4v_service()
    
    # 比較情報表示
    compare_with_old_system()
    
    # セットアップ手順
    if not success:
        setup_instructions()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ テスト完了 - GPT-4V統合準備完了!")
    else:
        print("⚠️ テスト失敗 - 上記の手順に従って設定してください")
    print("=" * 60)