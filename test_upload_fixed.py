#!/usr/bin/env python3
"""
동영상 업로드 및 OCR 처리 테스트
"""

import requests
import time
import os
from pathlib import Path

API_URL = "https://video-accounting-app.onrender.com"

def upload_video():
    """비디오 업로드"""
    print("비디오 업로드 중...")
    
    # 테스트 파일
    test_file = Path("uploads/videos/1753309926185.mp4")
    
    if not test_file.exists():
        print("테스트 파일이 없습니다. 더미 파일 사용...")
        files = {'file': ('test.mp4', b'dummy video data', 'video/mp4')}
        response = requests.post(f"{API_URL}/videos/", files=files)
    else:
        print(f"테스트 파일 사용: {test_file}")
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'video/mp4')}
            response = requests.post(f"{API_URL}/videos/", files=files)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 업로드 성공 - Video ID: {data['id']}")
        return data['id']
    else:
        print(f"❌ 업로드 실패: {response.status_code}")
        print(response.text)
        return None

def check_processing(video_id):
    """처리 상태 확인"""
    print(f"\n비디오 {video_id} 처리 상태 확인...")
    
    for i in range(30):  # 최대 5분 대기
        response = requests.get(f"{API_URL}/videos/{video_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            progress = data.get('progress', 0)
            message = data.get('progress_message', '')
            receipts = len(data.get('receipts', []))
            
            print(f"[{i+1}/30] Status: {status}, Progress: {progress}%, Receipts: {receipts}")
            print(f"         Message: {message}")
            
            if status == 'done':
                print(f"\n✅ 처리 완료! 영수증 {receipts}개 검출")
                return True
            elif status == 'error':
                print(f"\n❌ 처리 실패: {data.get('error_message')}")
                return False
        
        time.sleep(10)  # 10초 대기
    
    print("\n⏱️ 시간 초과")
    return False

def main():
    print("=" * 50)
    print("동영상 업로드 및 OCR 테스트")
    print("=" * 50)
    
    video_id = upload_video()
    if video_id:
        check_processing(video_id)
    
    print("\n테스트 완료")

if __name__ == "__main__":
    main()
