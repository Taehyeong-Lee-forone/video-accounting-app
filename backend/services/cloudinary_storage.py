"""
Cloudinary ストレージサービス
無料プランで十分な機能を提供
"""
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, Tuple
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class CloudinaryStorage:
    """Cloudinary統合ストレージサービス"""
    
    def __init__(self):
        # Cloudinary設定
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True
        )
        
        # 設定確認
        if not all([
            os.getenv("CLOUDINARY_CLOUD_NAME"),
            os.getenv("CLOUDINARY_API_KEY"),
            os.getenv("CLOUDINARY_API_SECRET")
        ]):
            logger.warning("Cloudinary credentials not fully configured")
            self.configured = False
        else:
            self.configured = True
            logger.info(f"Cloudinary configured for cloud: {os.getenv('CLOUDINARY_CLOUD_NAME')}")
    
    def upload_video(self, file_path: str, public_id: str = None) -> Tuple[bool, dict]:
        """
        ビデオをCloudinaryにアップロード
        
        Args:
            file_path: アップロードするファイルパス
            public_id: Cloudinary上での識別子（省略時は自動生成）
        
        Returns:
            (success, result_dict)
        """
        if not self.configured:
            return False, {"error": "Cloudinary not configured"}
        
        try:
            # ビデオアップロード設定
            upload_params = {
                "resource_type": "video",
                "folder": "video-accounting",  # フォルダ整理
                "use_filename": True,
                "unique_filename": True,
                "overwrite": False,
                "eager": [
                    {"width": 720, "height": 480, "crop": "limit", "quality": "auto"}  # 自動最適化
                ],
                "eager_async": True,  # 非同期処理
                "tags": ["accounting", "receipt"]
            }
            
            if public_id:
                upload_params["public_id"] = public_id
            
            # アップロード実行
            result = cloudinary.uploader.upload(file_path, **upload_params)
            
            logger.info(f"Video uploaded to Cloudinary: {result['public_id']}")
            logger.info(f"URL: {result['secure_url']}")
            
            return True, result
            
        except Exception as e:
            logger.error(f"Cloudinary upload error: {e}")
            return False, {"error": str(e)}
    
    def upload_video_from_bytes(self, file_bytes: bytes, filename: str, public_id: str = None) -> Tuple[bool, dict]:
        """
        バイトデータからビデオをアップロード
        
        Args:
            file_bytes: ビデオのバイトデータ
            filename: ファイル名
            public_id: Cloudinary上での識別子
        
        Returns:
            (success, result_dict)
        """
        if not self.configured:
            return False, {"error": "Cloudinary not configured"}
        
        try:
            # 一時ファイルに書き込み
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name
            
            # アップロード
            success, result = self.upload_video(tmp_path, public_id)
            
            # 一時ファイル削除
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return success, result
            
        except Exception as e:
            logger.error(f"Cloudinary upload from bytes error: {e}")
            return False, {"error": str(e)}
    
    def upload_image(self, file_path: str, public_id: str = None) -> Tuple[bool, dict]:
        """
        画像をCloudinaryにアップロード（領収書画像用）
        
        Args:
            file_path: アップロードする画像パス
            public_id: Cloudinary上での識別子
        
        Returns:
            (success, result_dict)
        """
        if not self.configured:
            return False, {"error": "Cloudinary not configured"}
        
        try:
            upload_params = {
                "folder": "video-accounting/receipts",
                "use_filename": True,
                "unique_filename": True,
                "overwrite": False,
                "transformation": [
                    {"quality": "auto:good"},  # 自動品質調整
                    {"fetch_format": "auto"}   # 自動フォーマット選択
                ],
                "tags": ["receipt", "accounting"]
            }
            
            if public_id:
                upload_params["public_id"] = public_id
            
            result = cloudinary.uploader.upload(file_path, **upload_params)
            
            logger.info(f"Image uploaded to Cloudinary: {result['public_id']}")
            
            return True, result
            
        except Exception as e:
            logger.error(f"Cloudinary image upload error: {e}")
            return False, {"error": str(e)}
    
    def get_video_url(self, public_id: str, transformation: dict = None) -> str:
        """
        ビデオのURLを取得
        
        Args:
            public_id: CloudinaryのパブリックID
            transformation: 変換オプション
        
        Returns:
            ビデオURL
        """
        if not self.configured:
            return ""
        
        try:
            if transformation:
                return cloudinary.utils.cloudinary_url(
                    public_id,
                    resource_type="video",
                    transformation=transformation,
                    secure=True
                )[0]
            else:
                return cloudinary.utils.cloudinary_url(
                    public_id,
                    resource_type="video",
                    secure=True
                )[0]
        except Exception as e:
            logger.error(f"Error getting video URL: {e}")
            return ""
    
    def delete_video(self, public_id: str) -> bool:
        """
        ビデオを削除
        
        Args:
            public_id: 削除するビデオのパブリックID
        
        Returns:
            成功/失敗
        """
        if not self.configured:
            return False
        
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type="video")
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Error deleting video: {e}")
            return False
    
    def get_resource_info(self, public_id: str) -> Optional[dict]:
        """
        リソース情報を取得
        
        Args:
            public_id: リソースのパブリックID
        
        Returns:
            リソース情報
        """
        if not self.configured:
            return None
        
        try:
            return cloudinary.api.resource(public_id, resource_type="video")
        except Exception as e:
            logger.error(f"Error getting resource info: {e}")
            return None
    
    def list_videos(self, max_results: int = 100) -> list:
        """
        アップロードされたビデオ一覧を取得
        
        Args:
            max_results: 最大取得数
        
        Returns:
            ビデオリスト
        """
        if not self.configured:
            return []
        
        try:
            result = cloudinary.api.resources(
                type="upload",
                resource_type="video",
                max_results=max_results,
                prefix="video-accounting/"
            )
            return result.get("resources", [])
        except Exception as e:
            logger.error(f"Error listing videos: {e}")
            return []

# グローバルインスタンス
cloudinary_storage = CloudinaryStorage()