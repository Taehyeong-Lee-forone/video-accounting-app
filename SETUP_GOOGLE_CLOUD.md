# Google Cloud設定完了チェックリスト

## 完了すべき作業:

1. [ ] Google Cloud Consoleでプロジェクト作成
   - プロジェクトID: ________________

2. [ ] 必要なAPIを有効化
   - [ ] Cloud Vision API
   - [ ] Cloud Storage
   - [ ] Video Intelligence API

3. [ ] サービスアカウント作成及びキーダウンロード
   - [ ] JSONキーファイルダウンロード完了

4. [ ] キーファイル設定
   - ダウンロードしたJSONファイルを`/Users/taehyeonglee/video-accounting-app/key.json`にコピー

5. [ ] Cloud Storageバケット作成（オプション）
   - バケット名: ________________

## 次のコマンドでキーファイルをコピー:
```bash
# ダウンロードフォルダからプロジェクトにコピー（Mac基準）
cp ~/Downloads/[ダウンロードしたキーファイル名].json /Users/taehyeonglee/video-accounting-app/key.json
```

## 環境変数アップデート:
`.env`ファイルに次を追加:
```
GCP_PROJECT_ID=your-project-id
GCS_BUCKET=your-bucket-name (オプション)
```