# Vercel 全スタック配置ガイド

## 📋 準備完了項目

✅ **構造変更完了**
- FastAPI → Vercel Functions に変換
- `/api` ディレクトリに Python Functions 配置
- Supabase Storage 直接アップロード対応

✅ **作成されたAPI**
- `/api/health` - ヘルスチェック
- `/api/videos/list` - ビデオ一覧取得
- `/api/videos/upload` - ビデオアップロード（Supabase Storage）
- `/api/videos/process` - OCR処理（Cron Job対応）

## 🚀 配置手順

### 1. GitHub リポジトリにプッシュ
```bash
git add .
git commit -m "feat: Vercel Functions対応に構造変更"
git push origin main
```

### 2. Vercel でプロジェクト作成
1. [vercel.com](https://vercel.com) にログイン
2. "New Project" クリック
3. GitHub リポジトリを選択
4. Framework Preset: "Next.js" を選択
5. Root Directory: `.` (プロジェクトルート)

### 3. 環境変数設定（Vercel Dashboard）

```bash
# Supabase
DATABASE_URL=postgresql://postgres:[YOUR-DB-PASSWORD]@db.dhbzrmokkyeevuphhkrd.supabase.co:5432/postgres
NEXT_PUBLIC_SUPABASE_URL=https://dhbzrmokkyeevuphhkrd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRoYnpybW9ra3llZXZ1cGhoa3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYxODI1ODIsImV4cCI6MjA3MTc1ODU4Mn0.jgEJY5oYjPkm8H8yw7vvP7prFRlrykNky1nlpNy2TFA
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRoYnpybW9ra3llZXZ1cGhoa3JkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjE4MjU4MiwiZXhwIjoyMDcxNzU4NTgyfQ.R3b574xt3YRBZMZt9d96OVk-CaddQqcgJLgP1LnfiV0

# Google Vision API (Base64エンコード済み)
GOOGLE_APPLICATION_CREDENTIALS_JSON=[YOUR-BASE64-ENCODED-JSON]

# API URL（自動設定）
NEXT_PUBLIC_API_URL=/api
```

### 4. デプロイ実行
```bash
vercel --prod
```

## 📝 制限事項と回避策

### 現在の制限
1. **ビデオ処理**: 10秒制限のため簡易処理のみ
2. **ファイルサイズ**: 関数の本体サイズ50MB制限
3. **FFmpeg**: 使用不可（外部サービス必要）

### 今後の改善案

#### Phase 1: 基本機能（実装済み）
- ✅ 画像/PDFアップロード
- ✅ OCR処理
- ✅ データベース保存

#### Phase 2: ビデオ処理改善
- [ ] Cloudflare Stream統合（ビデオ処理）
- [ ] AWS Lambda連携（重い処理）
- [ ] Edge Functions活用

#### Phase 3: パフォーマンス最適化
- [ ] ISR（増分静的再生成）
- [ ] Edge Middleware でキャッシュ
- [ ] Webhook による非同期処理

## 🔧 ローカル開発

### Backend API テスト
```bash
# Vercel CLI インストール
npm i -g vercel

# ローカル実行
vercel dev
```

### Frontend 開発
```bash
cd frontend
npm run dev
```

## 📊 監視とデバッグ

### Vercel Dashboard で確認
- Functions タブ: API実行ログ
- Analytics: パフォーマンス監視
- Crons: 定期実行状況

### エラー時の確認項目
1. 環境変数が正しく設定されているか
2. Supabase のRLSポリシーが適切か
3. Google Vision API の割り当て制限
4. Function のタイムアウト設定

## 🎯 次のステップ

1. **Google Vision API キー取得**
   - Service Account 作成
   - Base64 エンコード
   - 環境変数に設定

2. **Supabase Storage ポリシー設定**
   ```sql
   -- videos バケットのポリシー
   CREATE POLICY "Allow public read" ON storage.objects
   FOR SELECT USING (bucket_id = 'videos');
   
   CREATE POLICY "Allow authenticated upload" ON storage.objects
   FOR INSERT WITH CHECK (bucket_id = 'videos');
   ```

3. **本番デプロイ**
   ```bash
   vercel --prod
   ```

## 💰 コスト管理

### 無料枠
- Vercel: 100GB帯域幅/月
- Supabase: 1GB Storage, 500MB DB
- Google Vision: 1000ユニット/月

### 最適化のヒント
- 画像を圧縮してからアップロード
- OCRは必要な部分のみ実行
- キャッシュを積極的に活用

---

**サポート**: 問題が発生した場合は、Vercelのログを確認し、環境変数の設定を再確認してください。