# ngrok共有設定手順

## 1. ngrokトンネル起動後の設定

### フロントエンドURL（例）:
```
https://abc123xyz.ngrok-free.app
```

### バックエンドURL（例）:
```
https://def456uvw.ngrok-free.app
```

## 2. frontend/.env.localを更新

```bash
# バックエンドのngrok URLに更新
NEXT_PUBLIC_API_URL=https://def456uvw.ngrok-free.app
```

## 3. フロントエンドを再起動

```bash
# Ctrl+C で一度停止してから
cd frontend
npm run dev
```

## 4. 共有用メッセージテンプレート

```
【動画会計アプリ テスト版】

📱 アクセスURL: https://abc123xyz.ngrok-free.app

🚀 使い方:
1. URLをクリック
2. 「Visit Site」ボタンをクリック（ngrokの警告画面が出ます）
3. 動画をアップロードして試してください

⚠️ 注意事項:
- このURLは本日のみ有効です
- 初回アクセス時に警告が出ますが、安全です
- テストデータのみ使用してください
- 動画は30秒以内を推奨

💬 フィードバック:
- 使いにくい点
- エラーが出た場合のスクリーンショット
- 改善要望

よろしくお願いします！
```

## 5. トラブルシューティング

### 「Visit Site」ボタンが表示される
→ これはngrokの仕様です。クリックして進んでください。

### 動画が再生されない
→ ブラウザのキャッシュをクリアしてリロード

### APIエラーが出る
→ バックエンドのngrok URLが正しく設定されているか確認

## 6. セッション管理

ngrokのWeb UI で状態確認:
http://127.0.0.1:4040

ここでリクエストの詳細を確認できます。