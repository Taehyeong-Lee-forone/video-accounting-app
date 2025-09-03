"""
Cloudinary統合テスト
"""
import os
import sys
from pathlib import Path

# バックエンドディレクトリをパスに追加
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

def test_cloudinary_setup():
    """Cloudinary設定確認"""
    print("=== Cloudinary設定確認 ===")
    
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    
    if not cloud_name:
        print("❌ CLOUDINARY_CLOUD_NAME が設定されていません")
        print("\n1. Cloudinaryアカウントを作成: https://cloudinary.com/users/register/free")
        print("2. ダッシュボードから認証情報を取得")
        print("3. .envファイルに追加:")
        print("   CLOUDINARY_CLOUD_NAME=your_cloud_name")
        print("   CLOUDINARY_API_KEY=your_api_key")
        print("   CLOUDINARY_API_SECRET=your_api_secret")
        return False
    
    if not api_key:
        print("❌ CLOUDINARY_API_KEY が設定されていません")
        return False
    
    if not api_secret:
        print("❌ CLOUDINARY_API_SECRET が設定されていません")
        return False
    
    print(f"✅ Cloudinary設定完了")
    print(f"   Cloud Name: {cloud_name}")
    print(f"   API Key: {api_key[:10]}...")
    
    return True

def test_cloudinary_upload():
    """Cloudinaryアップロードテスト"""
    from services.cloudinary_storage import CloudinaryStorage
    
    print("\n=== Cloudinaryアップロードテスト ===")
    
    storage = CloudinaryStorage()
    
    if not storage.configured:
        print("❌ Cloudinaryが設定されていません")
        return False
    
    # テスト用の小さな動画ファイルを探す
    test_files = [
        "uploads/videos/1753309926185.mp4",
        "backend/uploads/videos/1753309926185.mp4",
        "test_video.mp4"
    ]
    
    test_file = None
    for file in test_files:
        if os.path.exists(file):
            test_file = file
            break
    
    if not test_file:
        print("⚠️ テスト用動画ファイルが見つかりません")
        print("小さなテスト動画を作成します...")
        
        # 簡単なテスト動画を作成（黒い画面の1秒動画）
        import subprocess
        test_file = "test_video.mp4"
        try:
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1",
                "-c:v", "libx264", "-t", "1", test_file
            ], check=True, capture_output=True)
            print(f"✅ テスト動画作成: {test_file}")
        except Exception as e:
            print(f"❌ テスト動画作成失敗: {e}")
            return False
    
    print(f"📁 テストファイル: {test_file}")
    print(f"   サイズ: {os.path.getsize(test_file) / 1024:.1f} KB")
    
    # アップロードテスト
    print("\n📤 Cloudinaryにアップロード中...")
    success, result = storage.upload_video(test_file, public_id="test_video_upload")
    
    if success:
        print("✅ アップロード成功！")
        print(f"   Public ID: {result.get('public_id')}")
        print(f"   URL: {result.get('secure_url')}")
        print(f"   サイズ: {result.get('bytes', 0) / 1024:.1f} KB")
        print(f"   形式: {result.get('format')}")
        
        # URLアクセステスト
        import requests
        response = requests.head(result.get('secure_url'))
        if response.status_code == 200:
            print("✅ URLアクセス確認OK")
        else:
            print(f"⚠️ URLアクセスエラー: {response.status_code}")
        
        # 削除テスト
        print("\n🗑️ テストファイル削除中...")
        if storage.delete_video(result.get('public_id')):
            print("✅ 削除成功")
        else:
            print("⚠️ 削除失敗")
        
        return True
    else:
        print("❌ アップロード失敗")
        print(f"   エラー: {result}")
        return False

def test_storage_service():
    """StorageService統合テスト"""
    print("\n=== StorageService統合テスト ===")
    
    # STORAGE_TYPEをcloudinaryに設定
    os.environ["STORAGE_TYPE"] = "cloudinary"
    
    from services.storage import StorageService
    
    try:
        storage = StorageService()
        print(f"✅ StorageService初期化成功")
        print(f"   ストレージタイプ: {storage.storage_type}")
        
        # テスト用バイトデータ
        test_data = b"Test video content"
        
        # アップロードテスト
        print("\n📤 バイトデータアップロードテスト...")
        success, url = storage.upload_file_sync(
            file_content=test_data,
            file_path="test/integration/test.mp4",
            content_type="video/mp4"
        )
        
        if success:
            print(f"✅ アップロード成功: {url}")
            
            # URLテスト
            import requests
            response = requests.head(url)
            print(f"   URLステータス: {response.status_code}")
            
            return True
        else:
            print(f"❌ アップロード失敗: {url}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Cloudinary統合テストスクリプト")
    print("=" * 50)
    
    # 設定確認
    if not test_cloudinary_setup():
        print("\n⚠️ Cloudinary設定を完了してください")
        return
    
    # アップロードテスト
    if test_cloudinary_upload():
        print("\n✅ Cloudinaryアップロードテスト成功")
    else:
        print("\n❌ Cloudinaryアップロードテスト失敗")
    
    # StorageService統合テスト
    if test_storage_service():
        print("\n✅ StorageService統合テスト成功")
    else:
        print("\n❌ StorageService統合テスト失敗")
    
    print("\n" + "=" * 50)
    print("テスト完了")

if __name__ == "__main__":
    main()