#!/bin/bash

echo "==================================="
echo "Google Cloud Vision API設定スクリプト"
echo "==================================="

# 1. 必要なPythonパッケージインストール
echo ""
echo "1. Pythonパッケージインストール中..."
pip install google-cloud-vision

# 2. gcloud CLI確認
echo ""
echo "2. gcloud CLI確認..."
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLIがインストールされていません。"
    echo "   次のリンクからインストールしてください: https://cloud.google.com/sdk/docs/install"
    exit 1
else
    echo "✅ gcloud CLI発見"
fi

# 3. 現在の認証状態確認
echo ""
echo "3. 現在のgcloud認証状態:"
gcloud auth list

# 4. プロジェクト設定
echo ""
echo "4. 現在のプロジェクト:"
gcloud config get-value project

# 5. Vision API有効化確認
echo ""
echo "5. Vision API状態確認..."
PROJECT_ID=$(gcloud config get-value project)
if [ ! -z "$PROJECT_ID" ]; then
    API_STATUS=$(gcloud services list --filter="vision.googleapis.com" --format="value(state)" 2>/dev/null)
    if [ "$API_STATUS" == "ENABLED" ]; then
        echo "✅ Vision APIがすでに有効化されています。"
    else
        echo "⚠️  Vision APIが有効化されていません。"
        echo "   有効化しますか？ (y/n)"
        read -r response
        if [ "$response" = "y" ]; then
            gcloud services enable vision.googleapis.com
            echo "✅ Vision API有効化完了"
        fi
    fi
fi

# 6. Application Default Credentials設定
echo ""
echo "6. Application Default Credentials設定"
echo "   (JSONキーなしでローカルかVision API使用)"
echo ""
echo "次のコマンドを実行して認証を完了してください:"
echo ""
echo "  gcloud auth application-default login"
echo ""
echo "ブラウザが開いたらGoogleアカウントでログインしてください。"
echo ""
echo "==================================="
echo "設定完了後、次を確認してください:"
echo ""
echo "1. .envファイルでUSE_VISION_API=true設定"
echo "2. サーバー再起動: python3 main.py"
echo "==================================="