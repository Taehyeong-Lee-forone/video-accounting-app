#!/usr/bin/env python3
import requests
import time

BASE_URL = "http://localhost:8000/api"

print("🔍 レシート検出デバッグ...")
print("ビデオアップロード中...")

with open("/Users/taehyeonglee/video-accounting-app/backend/uploads/videos/multi_receipt.mp4", "rb") as f:
    files = {"file": ("debug_test.mp4", f, "video/mp4")}
    response = requests.post(f"{BASE_URL}/videos/", files=files)

video_data = response.json()
video_id = video_data["id"]
print(f"Video ID: {video_id}")

print("分析開始...")
response = requests.post(
    f"{BASE_URL}/videos/{video_id}/analyze",
    json={"frames_per_second": 2}
)

print("10秒待機...")
time.sleep(10)

response = requests.get(f"{BASE_URL}/videos/{video_id}")
video_data = response.json()

print(f"Status: {video_data.get('status')}")
print(f"Receipts found: {len(video_data.get('receipts', []))}")

for r in video_data.get('receipts', []):
    print(f"  - {r.get('vendor')}: frame_id={r.get('best_frame_id')}")