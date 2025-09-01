"""
クラウドストレージサービス (Supabase Storage / S3 / GCS)
"""
import os
import hashlib
from typing import Optional, Tuple
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class StorageService:
    """クラウドストレージ統合サービス"""
    
    def __init__(self):
        self.storage_type = os.getenv("STORAGE_TYPE", "supabase")  # supabase, s3, gcs
        
        if self.storage_type == "supabase":
            self._init_supabase()
        elif self.storage_type == "s3":
            self._init_s3()
        elif self.storage_type == "gcs":
            self._init_gcs()
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    def _init_supabase(self):
        """Supabase Storage初期化"""
        from supabase import create_client, Client
        
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self.bucket_name = os.getenv("SUPABASE_BUCKET", "videos")
    
    def _init_s3(self):
        """AWS S3初期化"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "video-accounting-app")
    
    def _init_gcs(self):
        """Google Cloud Storage初期化"""
        from google.cloud import storage
        
        # GCSの認証はGOOGLE_APPLICATION_CREDENTIALS環境変数で設定
        self.gcs_client = storage.Client()
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "video-accounting-app")
        self.bucket = self.gcs_client.bucket(self.bucket_name)
    
    def generate_file_path(self, user_id: int, filename: str, file_type: str = "video") -> str:
        """
        ユーザーごとの整理されたファイルパスを生成
        
        例: users/123/videos/2024/01/hash_filename.mp4
        """
        # ファイル名のハッシュ化（セキュリティ向上）
        file_hash = hashlib.md5(f"{user_id}_{filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        
        # 拡張子取得
        ext = os.path.splitext(filename)[1] or '.mp4'
        
        # 日付ベースのディレクトリ構造
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        # パス生成
        path = f"users/{user_id}/{file_type}s/{year}/{month}/{file_hash}_{filename}"
        
        return path
    
    async def upload_file(self, file_content: bytes, file_path: str, content_type: str = None) -> Tuple[bool, str]:
        """
        ファイルをクラウドストレージにアップロード
        
        Returns:
            (success: bool, url_or_error: str)
        """
        try:
            if self.storage_type == "supabase":
                return await self._upload_supabase(file_content, file_path, content_type)
            elif self.storage_type == "s3":
                return await self._upload_s3(file_content, file_path, content_type)
            elif self.storage_type == "gcs":
                return await self._upload_gcs(file_content, file_path, content_type)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False, str(e)
    
    def upload_file_sync(self, file_content: bytes, file_path: str, content_type: str = None) -> Tuple[bool, str]:
        """
        同期版アップロード
        
        Returns:
            (success: bool, url_or_error: str)
        """
        try:
            if self.storage_type == "supabase":
                return self._upload_supabase_sync(file_content, file_path, content_type)
            elif self.storage_type == "s3":
                return self._upload_s3_sync(file_content, file_path, content_type)
            elif self.storage_type == "gcs":
                return self._upload_gcs_sync(file_content, file_path, content_type)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False, str(e)
    
    def _upload_supabase_sync(self, file_content: bytes, file_path: str, content_type: str) -> Tuple[bool, str]:
        """Supabase Storageに同期アップロード"""
        try:
            # Supabase Storageにアップロード
            response = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": content_type or "video/mp4", "upsert": "true"}
            )
            
            # レスポンスを確認
            logger.info(f"Supabase upload response: {response}")
            
            # エラーチェック
            if hasattr(response, 'error') and response.error:
                logger.error(f"Supabase upload error: {response.error}")
                return False, str(response.error)
            
            # 公開URLを取得
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
            
            logger.info(f"Uploaded to Supabase: {file_path}, URL: {public_url}")
            return True, public_url
        except Exception as e:
            logger.error(f"Supabase upload error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, str(e)
    
    async def _upload_supabase(self, file_content: bytes, file_path: str, content_type: str) -> Tuple[bool, str]:
        """Supabase Storageにアップロード"""
        try:
            # Supabase Storageにアップロード
            response = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": content_type or "video/mp4"}
            )
            
            # 公開URLを取得
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
            
            logger.info(f"Uploaded to Supabase: {file_path}")
            return True, public_url
        except Exception as e:
            logger.error(f"Supabase upload error: {e}")
            return False, str(e)
    
    def _upload_s3_sync(self, file_content: bytes, file_path: str, content_type: str) -> Tuple[bool, str]:
        """AWS S3に同期アップロード"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=file_content,
                ContentType=content_type or "video/mp4"
            )
            
            # 署名付きURL生成（7日間有効）
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_path},
                ExpiresIn=604800  # 7 days
            )
            
            logger.info(f"Uploaded to S3: {file_path}")
            return True, url
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            return False, str(e)
    
    def _upload_gcs_sync(self, file_content: bytes, file_path: str, content_type: str) -> Tuple[bool, str]:
        """Google Cloud Storageに同期アップロード"""
        try:
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(file_content, content_type=content_type or "video/mp4")
            
            # 公開URLを取得
            url = blob.public_url
            
            logger.info(f"Uploaded to GCS: {file_path}")
            return True, url
        except Exception as e:
            logger.error(f"GCS upload error: {e}")
            return False, str(e)
    
    async def _upload_s3(self, file_content: bytes, file_path: str, content_type: str) -> Tuple[bool, str]:
        """AWS S3にアップロード"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=file_content,
                ContentType=content_type or "video/mp4"
            )
            
            # 署名付きURL生成（7日間有効）
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_path},
                ExpiresIn=604800  # 7 days
            )
            
            logger.info(f"Uploaded to S3: {file_path}")
            return True, url
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            return False, str(e)
    
    async def _upload_gcs(self, file_content: bytes, file_path: str, content_type: str) -> Tuple[bool, str]:
        """Google Cloud Storageにアップロード"""
        try:
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(file_content, content_type=content_type or "video/mp4")
            
            # 公開URLを取得
            url = blob.public_url
            
            logger.info(f"Uploaded to GCS: {file_path}")
            return True, url
        except Exception as e:
            logger.error(f"GCS upload error: {e}")
            return False, str(e)
    
    async def download_file(self, file_path: str) -> Optional[bytes]:
        """
        クラウドストレージからファイルをダウンロード
        """
        try:
            if self.storage_type == "supabase":
                return await self._download_supabase(file_path)
            elif self.storage_type == "s3":
                return await self._download_s3(file_path)
            elif self.storage_type == "gcs":
                return await self._download_gcs(file_path)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    async def _download_supabase(self, file_path: str) -> Optional[bytes]:
        """Supabase Storageからダウンロード"""
        try:
            response = self.client.storage.from_(self.bucket_name).download(file_path)
            return response
        except Exception as e:
            logger.error(f"Supabase download error: {e}")
            return None
    
    async def _download_s3(self, file_path: str) -> Optional[bytes]:
        """AWS S3からダウンロード"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"S3 download error: {e}")
            return None
    
    async def _download_gcs(self, file_path: str) -> Optional[bytes]:
        """Google Cloud Storageからダウンロード"""
        try:
            blob = self.bucket.blob(file_path)
            return blob.download_as_bytes()
        except Exception as e:
            logger.error(f"GCS download error: {e}")
            return None
    
    async def delete_file(self, file_path: str) -> bool:
        """
        クラウドストレージからファイルを削除
        """
        try:
            if self.storage_type == "supabase":
                self.client.storage.from_(self.bucket_name).remove([file_path])
            elif self.storage_type == "s3":
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            elif self.storage_type == "gcs":
                blob = self.bucket.blob(file_path)
                blob.delete()
            
            logger.info(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    def get_public_url(self, file_path: str) -> str:
        """
        ファイルの公開URLを取得（既存ファイル用）
        """
        if self.storage_type == "supabase":
            return self.client.storage.from_(self.bucket_name).get_public_url(file_path)
        elif self.storage_type == "s3":
            return f"https://{self.bucket_name}.s3.amazonaws.com/{file_path}"
        elif self.storage_type == "gcs":
            return f"https://storage.googleapis.com/{self.bucket_name}/{file_path}"
        
        return ""