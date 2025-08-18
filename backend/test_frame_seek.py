#!/usr/bin/env python3
"""Test frame seeking accuracy"""

import cv2
import sys

def test_frame_seek(video_path, time_ms):
    """Test different seeking methods"""
    cap = cv2.VideoCapture(video_path)
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_ms = int(total_frames * 1000 / fps)
    
    print(f"Video info: FPS={fps}, Total frames={total_frames}, Duration={duration_ms}ms")
    print(f"Target time: {time_ms}ms")
    print("-" * 50)
    
    # Method 1: Seek by milliseconds (original method)
    cap.set(cv2.CAP_PROP_POS_MSEC, time_ms)
    actual_ms_1 = cap.get(cv2.CAP_PROP_POS_MSEC)
    actual_frame_1 = cap.get(cv2.CAP_PROP_POS_FRAMES)
    print(f"Method 1 (CAP_PROP_POS_MSEC):")
    print(f"  Requested: {time_ms}ms")
    print(f"  Actual: {actual_ms_1}ms (frame {actual_frame_1})")
    print(f"  Difference: {abs(actual_ms_1 - time_ms)}ms")
    
    # Method 2: Seek by frame number (new method)
    target_frame = int(time_ms * fps / 1000.0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    actual_frame_2 = cap.get(cv2.CAP_PROP_POS_FRAMES)
    actual_ms_2 = cap.get(cv2.CAP_PROP_POS_MSEC)
    print(f"\nMethod 2 (CAP_PROP_POS_FRAMES):")
    print(f"  Target frame: {target_frame}")
    print(f"  Actual frame: {actual_frame_2}")
    print(f"  Actual time: {actual_ms_2}ms")
    print(f"  Difference: {abs(actual_ms_2 - time_ms)}ms")
    
    cap.release()

if __name__ == "__main__":
    # Test with a sample video
    video_path = "uploads/videos/1753309926185.mp4"
    test_times = [6767, 7233, 10000, 15000]  # Test various times
    
    for time_ms in test_times:
        test_frame_seek(video_path, time_ms)
        print("\n" + "=" * 50 + "\n")