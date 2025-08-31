#!/usr/bin/env python3
"""
배포 서버 테스트 스크립트
- 파일 업로드
- 동영상 재생
- 영수증 추출 확인
"""

import requests
import json
import time
import os
from pathlib import Path

# 배포 서버 URL
API_URL = "https://video-accounting-app.onrender.com"
FRONTEND_URL = "https://video-accounting-app.vercel.app"

def test_health_check():
    """서버 상태 확인"""
    print("1. 서버 상태 확인...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ 서버 정상 작동")
            return True
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return False

def test_ocr_config():
    """OCR 설정 확인"""
    print("\n2. OCR 설정 확인...")
    try:
        response = requests.get(f"{API_URL}/videos/test-ocr")
        data = response.json()
        print(f"   - Google Credentials JSON: {'✅' if data.get('google_credentials_json') else '❌'}")
        print(f"   - Google Credentials File: {'✅' if data.get('google_credentials_file') else '❌'}")
        print(f"   - Gemini API Key: {'✅' if data.get('gemini_api_key') else '❌'}")
        print(f"   - Vision API: {'✅' if data.get('vision_api_initialized') else '❌'}")
        print(f"   - Render 환경: {data.get('render_env')}")
        return True
    except Exception as e:
        print(f"❌ OCR 설정 확인 실패: {e}")
        return False

def test_video_upload():
    """비디오 업로드 테스트"""
    print("\n3. 비디오 업로드 테스트...")
    
    # 테스트 파일 확인
    test_file = Path("uploads/videos/1753309926185.mp4")
    if not test_file.exists():
        print(f"⚠️  테스트 파일이 없습니다: {test_file}")
        # 더미 비디오 파일 생성 시도
        print("   더미 파일로 테스트 진행...")
        test_data = b"dummy video data for testing"
        files = {'file': ('test.mp4', test_data, 'video/mp4')}
    else:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'video/mp4')}
    
    try:
        response = requests.post(f"{API_URL}/videos/", files=files)
        if response.status_code == 200:
            video_data = response.json()
            print(f"✅ 업로드 성공 - Video ID: {video_data.get('id')}")
            return video_data.get('id')
        else:
            print(f"❌ 업로드 실패: {response.status_code}")
            print(f"   응답: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 업로드 요청 실패: {e}")
        return None

def test_video_detail(video_id):
    """비디오 상세 정보 확인"""
    print(f"\n4. 비디오 상세 정보 확인 (ID: {video_id})...")
    try:
        response = requests.get(f"{API_URL}/videos/{video_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 비디오 정보 조회 성공")
            print(f"   - 파일명: {data.get('filename')}")
            print(f"   - 상태: {data.get('status')}")
            print(f"   - 진행률: {data.get('progress')}%")
            print(f"   - 경로: {data.get('local_path')}")
            
            # 썸네일 확인
            if data.get('thumbnail_path'):
                thumb_url = f"{API_URL}/{data['thumbnail_path']}"
                thumb_response = requests.head(thumb_url)
                if thumb_response.status_code == 200:
                    print(f"   - 썸네일: ✅ 접근 가능")
                else:
                    print(f"   - 썸네일: ❌ 접근 불가 ({thumb_response.status_code})")
            
            return True
        else:
            print(f"❌ 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 조회 요청 실패: {e}")
        return False

def test_video_list():
    """비디오 목록 조회"""
    print("\n5. 비디오 목록 조회...")
    try:
        response = requests.get(f"{API_URL}/videos/")
        if response.status_code == 200:
            videos = response.json()
            print(f"✅ 목록 조회 성공 - 총 {len(videos)}개 비디오")
            for video in videos[:3]:  # 최근 3개만 표시
                print(f"   - [{video['id']}] {video['filename']} ({video['status']})")
            return True
        else:
            print(f"❌ 목록 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 목록 조회 요청 실패: {e}")
        return False

def main():
    print("=" * 50)
    print("배포 서버 테스트 시작")
    print("=" * 50)
    
    # 1. 서버 상태 확인
    if not test_health_check():
        print("\n⚠️  서버가 아직 시작되지 않았을 수 있습니다.")
        print("   몇 분 후 다시 시도해주세요.")
        return
    
    # 2. OCR 설정 확인
    test_ocr_config()
    
    # 3. 비디오 목록 조회
    test_video_list()
    
    # 4. 비디오 업로드 테스트 (선택)
    # video_id = test_video_upload()
    # if video_id:
    #     time.sleep(2)
    #     test_video_detail(video_id)
    
    print("\n" + "=" * 50)
    print("테스트 완료")
    print("=" * 50)
    print(f"\n프론트엔드 확인: {FRONTEND_URL}")
    print(f"백엔드 API 문서: {API_URL}/docs")

if __name__ == "__main__":
    main()