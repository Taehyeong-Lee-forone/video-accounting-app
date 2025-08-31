#!/usr/bin/env python3
"""
Supabase Storageバケット設定スクリプト
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

load_dotenv()

def setup_storage_bucket():
    """Supabase Storageバケットを作成"""
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        return False
    
    try:
        # Supabaseクライアント作成
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # バケット作成（既存の場合はスキップ）
        bucket_name = "videos"
        
        try:
            # バケット一覧取得
            buckets = supabase.storage.list_buckets()
            bucket_exists = any(b['name'] == bucket_name for b in buckets)
            
            if not bucket_exists:
                # バケット作成
                supabase.storage.create_bucket(
                    bucket_name,
                    options={
                        'public': False,  # プライベートバケット
                        'file_size_limit': 104857600,  # 100MB
                        'allowed_mime_types': ['video/*', 'image/*']
                    }
                )
                print(f"✅ Created bucket: {bucket_name}")
            else:
                print(f"✅ Bucket already exists: {bucket_name}")
            
            # CORSポリシー設定（必要に応じて）
            # これはSupabase Dashboardから設定する必要があります
            
            print("\n📝 Next steps:")
            print("1. Go to Supabase Dashboard > Storage")
            print("2. Click on 'videos' bucket")
            print("3. Go to Policies tab")
            print("4. Add these policies if not exists:")
            print("   - INSERT: authenticated users can upload to their folder")
            print("   - SELECT: authenticated users can view their files")
            print("   - DELETE: authenticated users can delete their files")
            print("\nExample policy (INSERT):")
            print("(auth.uid()::text = (storage.foldername(name))[1])")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating bucket: {e}")
            print("\nNote: You may need to create the bucket manually in Supabase Dashboard")
            return False
            
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False

if __name__ == "__main__":
    print("""
    ====================================
    Supabase Storage Setup
    ====================================
    """)
    
    if setup_storage_bucket():
        print("\n✅ Storage setup complete!")
    else:
        print("\n⚠️  Manual setup may be required")
        print("Go to: https://app.supabase.com/project/cphbbpvhfbmwqkcrhhwm/storage/buckets")