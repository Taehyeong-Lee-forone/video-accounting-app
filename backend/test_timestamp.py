#!/usr/bin/env python3
import cv2
import sys

video_path = "/Users/taehyeonglee/video-accounting-app/backend/uploads/videos/multi_receipt.mp4"

# ビデオを開く
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Failed to open video")
    sys.exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration_sec = total_frames / fps

print(f"Video Info:")
print(f"  FPS: {fps}")
print(f"  Total frames: {total_frames}")
print(f"  Duration: {duration_sec:.2f} seconds")
print()

# サンプルフレームいくつか確認
sample_frames = [0, 30, 60, 90, 120, 150]
print("Sample frame timestamps:")

for frame_num in sample_frames:
    if frame_num >= total_frames:
        break
    
    # フレーム番号で移動
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    
    # 現在位置確認
    current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
    current_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
    calculated_ms = (frame_num / fps) * 1000
    
    print(f"  Frame {frame_num:3d}: OpenCV={current_ms:7.1f}ms, Calculated={calculated_ms:7.1f}ms, Diff={abs(current_ms-calculated_ms):5.1f}ms")

cap.release()

# 予想レシート位置（おおよそ）
print("\n予想レシート位置 (1.5秒間隔):")
for i in range(int(duration_sec / 1.5) + 1):
    time_sec = i * 1.5
    if time_sec <= duration_sec:
        print(f"  レシート {i+1}: {time_sec:.1f}秒 ({int(time_sec*1000)}ms)")