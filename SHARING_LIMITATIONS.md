# ⚠️ 外部共有の制限事項

## 現在の構造での制限

### ❌ できないこと:
1. **外部からの動画アップロード**
   - ファイルはあなたのローカルマシンに保存される
   - 他のユーザーがアップロードしても、あなたのPCにしか保存されない

2. **データの永続化**
   - SQLiteデータベースはローカル
   - 外部ユーザーのデータは共有されない

3. **完全な機能の共有**
   - 動画処理、OCR、仕訳生成はローカル処理

### ✅ できること:
- **UIの確認のみ**
- **デザインレビュー**
- **画面遷移の確認**

## 真の外部共有のための必要事項

### 1. クラウドストレージ
```javascript
// 現在の実装（ローカル）
const file = await saveToLocal('/uploads/videos/...')

// 必要な実装（クラウド）
const file = await uploadToCloudStorage('gs://bucket/videos/...')
```

### 2. クラウドデータベース
- SQLite → PostgreSQL/MySQL
- ローカル → クラウドホスティング

### 3. 完全クラウドデプロイ

#### 最速の解決策: Render.com（無料）

1. **GitHubにプッシュ**
```bash
git init
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Render.comでデプロイ**
- Backend: Web Service
- Database: PostgreSQL
- Frontend: Static Site

3. **環境変数の設定**
```
DATABASE_URL=postgresql://...
GOOGLE_API_KEY=...
```

## 今すぐできる対処法

### Option A: デモ動画を作成
```bash
# ローカルで動作を録画
# 動画を共有
```

### Option B: 画面共有セッション
- Zoom/Teamsで画面共有
- リアルタイムでデモ

### Option C: 最小限のクラウド化
1. データベースだけクラウド化（Supabase無料）
2. ファイルは一時的にBase64で送信
3. 小さいファイルのみ対応

## 技術的な改修必要箇所

### Backend (main.py)
```python
# 現在
app.mount("/uploads", StaticFiles(directory="uploads"))

# 必要
# Cloud Storage SDKを使用
```

### Frontend
```javascript
// 現在
const formData = new FormData()
formData.append('file', file)

// そのまま使える（APIエンドポイントを変更するだけ）
```

## 結論

**現在のngrok/Cloudflareトンネル構成では:**
- ✅ UIの表示は可能
- ❌ 実際の動画処理は不可能
- ❌ データの共有は不可能

**本当の外部共有には:**
- クラウドインフラが必須
- 最低でも2-3時間の設定作業が必要

---

最終更新: 2025年8月18日