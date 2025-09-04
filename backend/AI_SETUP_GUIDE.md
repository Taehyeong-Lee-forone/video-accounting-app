# AI API 設定ガイド

## Gemini API から OpenAI GPT-4 への切り替え方法

### 1. OpenAI API キーの取得

1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. アカウントを作成またはログイン
3. API Keys セクションで新しいAPIキーを生成
4. キーをコピー

### 2. 環境変数の設定

`.env` ファイルを編集:

```bash
# AI API設定
# OpenAI API（GPT-4を使用）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxx

# AI選択（gemini または openai）
AI_PROVIDER=openai

# Gemini APIキー（バックアップ用に残しておく）
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxx
```

### 3. 依存パッケージのインストール

```bash
pip install openai==1.35.0
```

または

```bash
pip install -r requirements.txt
```

### 4. 切り替え確認

サーバーを再起動:

```bash
python -m uvicorn main:app --reload
```

ログで以下が表示されれば成功:
```
INFO: OpenAI GPT-4 service initialized
```

## 比較表

| 機能 | Gemini | OpenAI GPT-4 |
|------|--------|--------------|
| 日本語OCR精度 | 高 | 非常に高 |
| レスポンス速度 | 速い | やや遅い |
| コスト | 安い | 高い |
| JSON出力 | 不安定な場合あり | 安定（構造化出力対応） |
| 画像処理 | gemini-1.5-flash | gpt-4o (Vision) |

## トラブルシューティング

### OpenAI APIが動作しない場合

1. APIキーが正しいか確認
2. OpenAIアカウントに残高があるか確認
3. ログを確認:
   ```bash
   tail -f logs/app.log
   ```

### Geminiに戻したい場合

`.env` ファイルを編集:
```bash
AI_PROVIDER=gemini
```

## 推奨設定

- **開発環境**: Gemini（コスト効率が良い）
- **本番環境**: OpenAI GPT-4（精度重視）

## テスト方法

```bash
# テストスクリプト実行
python test_ai_service.py
```

## 注意事項

- OpenAI APIは従量課金制
- GPT-4は1リクエストあたり約$0.03-0.06
- 月間使用量を監視することを推奨
- 両方のAPIキーを設定しておけば、環境変数で簡単に切り替え可能