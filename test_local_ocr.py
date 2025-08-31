#!/usr/bin/env python3
"""
로컬 OCR 테스트 스크립트
"""

import os
import sys

# 환경 변수 설정 (로컬 테스트용)
os.environ["RENDER"] = "false"

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pathlib import Path

def test_path_conversion():
    """경로 변환 로직 테스트"""
    print("=" * 50)
    print("경로 변환 테스트")
    print("=" * 50)
    
    # 테스트 케이스
    test_cases = [
        ("uploads/videos/test.mp4", "false", "uploads/videos/test.mp4"),
        ("uploads/videos/test.mp4", "true", "/tmp/videos/test.mp4"),
        ("/tmp/videos/test.mp4", "true", "/tmp/videos/test.mp4"),
    ]
    
    for path, render_env, expected in test_cases:
        os.environ["RENDER"] = render_env
        
        # 실제 변환 로직
        actual_path = path
        if os.getenv("RENDER") == "true" and actual_path.startswith("uploads/"):
            actual_path = actual_path.replace("uploads/", "/tmp/")
        
        status = "✅" if actual_path == expected else "❌"
        print(f"{status} RENDER={render_env}: {path} -> {actual_path}")
        if actual_path != expected:
            print(f"   Expected: {expected}")
    
    print()

def test_frame_directory():
    """프레임 디렉토리 설정 테스트"""
    print("=" * 50)
    print("프레임 디렉토리 테스트")
    print("=" * 50)
    
    for render_env in ["false", "true"]:
        os.environ["RENDER"] = render_env
        
        if os.getenv("RENDER") == "true":
            frames_dir = Path("/tmp/frames")
        else:
            base_path = Path(os.path.dirname(os.path.abspath(__file__)))
            frames_dir = base_path / "backend" / "uploads" / "frames"
        
        print(f"RENDER={render_env}: {frames_dir}")
        print(f"   존재 여부: {frames_dir.exists()}")
    
    print()

def test_video_file():
    """테스트 비디오 파일 확인"""
    print("=" * 50)
    print("테스트 비디오 파일")
    print("=" * 50)
    
    test_file = Path("uploads/videos/1753309926185.mp4")
    print(f"테스트 파일: {test_file}")
    print(f"   존재 여부: {test_file.exists()}")
    
    if test_file.exists():
        size = test_file.stat().st_size / 1024 / 1024
        print(f"   파일 크기: {size:.2f} MB")
    
    print()

def main():
    print("\n로컬 OCR 테스트 시작\n")
    
    test_path_conversion()
    test_frame_directory()
    test_video_file()
    
    print("테스트 완료\n")

if __name__ == "__main__":
    main()