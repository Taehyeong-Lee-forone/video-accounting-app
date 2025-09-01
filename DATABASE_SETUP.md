# データベース設定ガイド

## 現在の構成

### ローカル環境
- **データベース**: SQLite (`video_accounting.db`)
- **ファイルストレージ**: ローカル + Supabase Storage

### プロダクション環境 (Render)
- **データベース**: PostgreSQL (Render提供)
- **ファイルストレージ**: Supabase Storage

## ⚠️ 重要な注意事項

**ローカル環境とプロダクション環境は異なるデータベースを使用しています。**
これにより、以下の制限があります：

1. ローカルで作成したデータはプロダクションには表示されません
2. プロダクションで作成したデータはローカルには表示されません
3. 各環境は独立してデータを管理します

## 解決方法

### オプション 1: 環境を分離して使用（現在の設定）
- **メリット**: 
  - 開発環境とプロダクション環境が分離されて安全
  - ローカルテストがプロダクションに影響しない
- **デメリット**: 
  - データの同期が必要な場合は手動で行う必要がある

### オプション 2: Render PostgreSQLを共有使用
プロダクション環境と同じデータベースを使用したい場合：

1. **Render Dashboardから接続情報を取得**
   - Render Dashboard > Database > Connection
   - "External URL"をコピー

2. **ローカル.envファイルを更新**
   ```env
   # SQLiteをコメントアウト
   # DATABASE_URL=sqlite:///./video_accounting.db
   
   # Render PostgreSQLを有効化
   DATABASE_URL=postgresql://[取得したExternal URL]?sslmode=require
   ```

3. **注意事項**
   - SSL接続が必須（`sslmode=require`）
   - 外部接続はパフォーマンスが遅い可能性がある
   - IPアドレス制限がある場合は許可設定が必要

### オプション 3: Supabase PostgreSQLを使用
両環境で同じSupabase PostgreSQLを使用：

1. **Supabaseでデータベースを作成**
   - [Supabase Dashboard](https://app.supabase.com)にログイン
   - Settings > Database > Connection string

2. **両環境の設定を更新**
   - ローカル`.env`とRenderの環境変数を同じ接続文字列に設定

## トラブルシューティング

### SSL接続エラー
```
SSL connection has been closed unexpectedly
```
**解決方法**: 
- 接続文字列に`?sslmode=require`を追加
- `database.py`でSSL設定を確認

### 接続タイムアウト
**解決方法**:
- ファイアウォール設定を確認
- VPNを使用している場合は無効化

### データ移行
ローカルからプロダクションへデータを移行する場合：
```bash
# SQLiteからデータをエクスポート
sqlite3 video_accounting.db .dump > backup.sql

# PostgreSQLにインポート（要変換）
psql [DATABASE_URL] < backup_converted.sql
```

## 推奨設定

**開発環境**: SQLite（高速、簡単）
**プロダクション**: Render PostgreSQL（自動管理、バックアップ付き）

データ共有が必要な場合のみ、同じデータベースを使用することを検討してください。