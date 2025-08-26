"""
Supabase Storage接続ユーティリティ
"""
import os
from supabase import create_client, Client
from typing import BinaryIO, Optional

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

def get_supabase() -> Client:
    """Supabaseクライアント取得"""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def upload_file(
    bucket: str,
    file_path: str,
    file_data: BinaryIO,
    content_type: str = "application/octet-stream"
) -> str:
    """
    Supabase Storageにファイルアップロード
    
    Returns:
        public_url: 公開URL
    """
    supabase = get_supabase()
    
    # ファイルアップロード
    response = supabase.storage.from_(bucket).upload(
        file_path,
        file_data,
        {"content-type": content_type}
    )
    
    # 公開URL取得
    public_url = supabase.storage.from_(bucket).get_public_url(file_path)
    
    return public_url

def delete_file(bucket: str, file_path: str) -> bool:
    """Supabase Storageからファイル削除"""
    supabase = get_supabase()
    response = supabase.storage.from_(bucket).remove([file_path])
    return True

def get_file_url(bucket: str, file_path: str, expires_in: Optional[int] = None) -> str:
    """
    ファイルURL取得
    
    Args:
        expires_in: 有効期限（秒）、Noneの場合は公開URL
    """
    supabase = get_supabase()
    
    if expires_in:
        # 署名付きURL（期限付き）
        response = supabase.storage.from_(bucket).create_signed_url(
            file_path, 
            expires_in
        )
        return response.get("signedURL", "")
    else:
        # 公開URL
        return supabase.storage.from_(bucket).get_public_url(file_path)