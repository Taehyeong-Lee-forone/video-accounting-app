# MOVファイルアップロード問題の解決ガイド

## 問題の概要
AirdropでiPhoneからPCに転送したMOVファイル（QuickTimeムービー）がアップロードできない問題について。

## 考えられる原因

### 1. **MIMEタイプの問題**
- iPhoneのMOVファイルは `video/quicktime` として認識される
- ブラウザによっては `application/octet-stream` として送信される場合がある
- 一部のMOVファイルは `video/x-quicktime` として認識される

### 2. **コーデックの問題**
- iPhone 11以降のMOVファイルはHEVC(H.265)コーデックを使用
- 古いFFmpegバージョンではHEVCをサポートしていない可能性
- ProRes形式のMOVファイルは特殊な処理が必要

### 3. **ファイルサイズの問題**
- 4K動画などの大容量ファイル（100MB以上）
- アップロードタイムアウトが発生する可能性

## 実装した解決策

### フロントエンド改善
```javascript
// VideoUpload.tsx
accept: {
  'video/*': ['.mp4', '.mov', '.avi', '.webm', '.mkv'],
  'video/quicktime': ['.mov', '.qt'],  // QuickTime専用
  'video/mp4': ['.mp4', '.m4v'],
  'video/x-msvideo': ['.avi'],
  'video/webm': ['.webm'],
  'video/x-matroska': ['.mkv']
}
```

### バックエンド改善
```python
# videos_v2.py
# より柔軟なMIMEタイプ検証
valid_mime_types = [
    'video/mp4', 'video/quicktime', 'video/x-quicktime',
    'video/x-msvideo', 'video/avi',
    'video/webm', 'video/x-matroska',
    'application/octet-stream',  # ブラウザが判定できない場合
    'video/x-m4v'
]
```

## トラブルシューティング手順

### 1. **ブラウザコンソールでエラーを確認**
```javascript
// ブラウザのDevToolsコンソールで確認
// Network タブでアップロードリクエストの詳細を確認
```

### 2. **ファイル情報の確認（Mac）**
```bash
# ファイル形式の確認
file your_video.mov

# メタデータの確認
ffprobe your_video.mov

# コーデック情報の確認
ffmpeg -i your_video.mov
```

### 3. **ファイルの変換（必要な場合）**
```bash
# MOVをMP4に変換（H.264コーデック使用）
ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4

# HEVCのMOVをH.264のMP4に変換
ffmpeg -i input.mov -c:v libx264 -crf 23 -c:a aac output.mp4
```

## サーバーログの確認方法

### Render.comのログ確認
1. Render Dashboardにアクセス
2. 該当サービスを選択
3. Logs タブをクリック
4. アップロード時のエラーメッセージを確認

### ローカルでのデバッグ
```bash
# バックエンドサーバーを起動
cd backend
uvicorn main:app --reload --log-level debug

# ログでMIMEタイプとファイル名を確認
# 例: "Uploaded file: video.mov, MIME type: video/quicktime"
```

## 代替ソリューション

### 1. **ファイル変換アプリの使用**
- HandBrake（無料）
- VLC Media Player（無料）
- iMovie（Mac標準）

### 2. **iPhoneの録画設定変更**
設定 → カメラ → ビデオ撮影
- 「高効率」から「互換性優先」に変更
- これによりH.264形式で録画される

### 3. **Airdropの代替手段**
- iCloud Drive経由でアップロード
- Google Drive/Dropbox経由
- USB接続での直接転送

## 今後の改善案

1. **クライアントサイドでの変換**
   - FFmpeg.wasmを使用してブラウザ内で変換

2. **プログレッシブアップロード**
   - 大容量ファイルの分割アップロード実装

3. **自動コーデック検出と変換**
   - サーバーサイドでHEVCを自動的にH.264に変換

## サポートされているファイル形式一覧

| 拡張子 | MIMEタイプ | 説明 | 推奨 |
|-------|-----------|------|-----|
| .mp4 | video/mp4 | MPEG-4 Part 14 | ✅ 最も推奨 |
| .mov | video/quicktime | Apple QuickTime | ⚠️ 変換推奨 |
| .m4v | video/x-m4v | Apple iTunes | ✅ OK |
| .avi | video/x-msvideo | Microsoft AVI | ⚠️ 古い形式 |
| .webm | video/webm | WebM | ✅ Web最適化 |
| .mkv | video/x-matroska | Matroska | ⚠️ 大容量注意 |

## お問い合わせ
上記の方法でも解決しない場合は、以下の情報と共にサポートにお問い合わせください：
- 使用しているブラウザとバージョン
- iPhoneのモデルとiOSバージョン
- エラーメッセージのスクリーンショット
- ファイルサイズと録画設定