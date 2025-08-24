#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import time
import sys
import os

# APIエンドポイント
BASE_URL = "http://localhost:5001"

def test_video_upload():
    # テストファイルパス
    test_file = "/Users/taehyeonglee/video-accounting-app/backend/uploads/videos/1753309926185.mp4"
    
    # ファイル存在確認
    if not os.path.exists(test_file):
        print(f"❌ 테스트 파일이 없습니다: {test_file}")
        return None
    
    print(f"📁 테스트 파일: {test_file}")
    print(f"📊 파일 크기: {os.path.getsize(test_file) / (1024*1024):.2f} MB")
    
    # ビデオアップロード
    print("\n⬆️ 비디오 업로드 중...")
    with open(test_file, "rb") as f:
        files = {"file": ("1753309926185.mp4", f, "video/mp4")}
        response = requests.post(f"{BASE_URL}/videos/", files=files)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.status_code}")
        print(response.text)
        return None
    
    video_data = response.json()
    video_id = video_data["id"]
    print(f"Video uploaded successfully. ID: {video_id}")
    
    # 分析開始
    print("\n🔍 분석 시작 중...")
    response = requests.post(
        f"{BASE_URL}/videos/{video_id}/analyze",
        json={"frames_per_second": 2}
    )
    
    if response.status_code != 200:
        print(f"Analysis start failed: {response.status_code}")
        print(response.text)
        return None
    
    print("Analysis started successfully")
    
    # 完了まで待機
    print("\n⏳ 분석 완료 대기 중...")
    for i in range(60):  # 最大60秒待機
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/videos/{video_id}")
        if response.status_code == 200:
            video_data = response.json()
            status = video_data.get("status")
            progress = video_data.get("progress", 0)
            message = video_data.get("progress_message", "")
            
            print(f"Status: {status}, Progress: {progress}%, Message: {message}")
            
            if status == "done":
                print("\nAnalysis completed successfully!")
                print(f"Found {len(video_data.get('receipts', []))} receipts")
                for receipt in video_data.get('receipts', []):
                    print(f"  - {receipt.get('vendor')}: {receipt.get('document_type')}")
                return video_id
            elif status == "error":
                print(f"\nAnalysis failed: {video_data.get('error_message')}")
                return None
    
    print("\nAnalysis timed out")
    return None

if __name__ == "__main__":
    video_id = test_video_upload()
    if video_id:
        print(f"\nSuccess! Video ID: {video_id}")
        sys.exit(0)
    else:
        print("\nTest failed!")
        sys.exit(1)