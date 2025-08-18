#!/usr/bin/env python3
import requests
import time
import sys

# API endpoint
BASE_URL = "http://localhost:8000/api"

def test_video_upload():
    # Upload video
    print("Uploading video...")
    with open("/Users/taehyeonglee/video-accounting-app/backend/uploads/videos/multi_receipt.mp4", "rb") as f:
        files = {"file": ("test_video.mp4", f, "video/mp4")}
        response = requests.post(f"{BASE_URL}/videos/", files=files)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.status_code}")
        print(response.text)
        return None
    
    video_data = response.json()
    video_id = video_data["id"]
    print(f"Video uploaded successfully. ID: {video_id}")
    
    # Start analysis
    print("Starting analysis...")
    response = requests.post(
        f"{BASE_URL}/videos/{video_id}/analyze",
        json={"frames_per_second": 2}
    )
    
    if response.status_code != 200:
        print(f"Analysis start failed: {response.status_code}")
        print(response.text)
        return None
    
    print("Analysis started successfully")
    
    # Poll for completion
    print("Waiting for analysis to complete...")
    for i in range(60):  # Wait up to 60 seconds
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