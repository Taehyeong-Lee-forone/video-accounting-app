"""
Application Configuration
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    app_name: str = "Video Accounting API"
    debug: bool = False
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./videoaccounting.db"
    )
    
    # If using PostgreSQL, convert URL format
    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            # Heroku/Railway uses postgres://, SQLAlchemy needs postgresql://
            return self.database_url.replace("postgres://", "postgresql://", 1)
        return self.database_url
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: list = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:3001"
    ).split(",")
    
    # Google Cloud
    google_application_credentials_json: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    google_cloud_project_id: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    
    # Storage
    storage_type: str = os.getenv("STORAGE_TYPE", "local")  # local, supabase, gcs, s3
    
    # Supabase
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    supabase_service_key: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    supabase_storage_bucket: str = os.getenv("SUPABASE_STORAGE_BUCKET", "videos")
    
    # AWS S3
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_bucket_name: Optional[str] = os.getenv("S3_BUCKET_NAME")
    s3_region: str = os.getenv("S3_REGION", "ap-northeast-1")
    
    # GCS
    gcs_bucket_name: Optional[str] = os.getenv("GCS_BUCKET_NAME")
    
    # File Upload
    max_upload_size: int = 500 * 1024 * 1024  # 500MB
    allowed_extensions: list = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    
    # Processing
    video_fps: float = 1.0  # Frames per second for analysis
    max_frames_per_video: int = 300
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()