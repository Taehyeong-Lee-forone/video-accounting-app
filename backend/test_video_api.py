#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Video Intelligence API 接続テストスクリプト
"""

import os
import sys
from google.cloud import videointelligence
from google.api_core import exceptions

def test_video_intelligence_connection():
    """
    # Video Intelligence API接続をテストする
    """
    print("Video Intelligence API 연결 테스트 시작...")
    
    try:
        # クライアントを初期化
        client = videointelligence.VideoIntelligenceServiceClient()
        print("✅ Video Intelligence 클라이언트 초기화 성공!")
        
        # プロジェクトIDを取得
        from google.auth import default
        credentials, project_id = default()
        print(f"✅ 프로젝트 ID: {project_id}")
        print(f"✅ 인증 파일 위치: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'Application Default Credentials 사용')}")
        
        # 簡単なテストリクエストを送信（実際のビデオなしで）
        try:
            # サンプルGSビデオでテスト（Googleが提供するサンプル）
            test_video_uri = "gs://cloud-samples-data/video/cat.mp4"
            features = [videointelligence.Feature.LABEL_DETECTION]
            
            print(f"\n테스트 비디오로 API 호출 시도: {test_video_uri}")
            
            # 非同期操作を開始
            operation = client.annotate_video(
                request={
                    "input_uri": test_video_uri,
                    "features": features,
                }
            )
            
            print("⏳ API 요청 전송 성공! 응답 대기 중...")
            
            # タイムアウトを短くして、API接続だけテスト
            result = operation.result(timeout=30)
            
            print("✅ Video Intelligence API 연결 및 테스트 성공!")
            
            # 結果の簡単な確認
            if result.annotation_results:
                print(f"✅ 분석 결과 수신: {len(result.annotation_results)} 세그먼트")
                
        except exceptions.PermissionDenied as e:
            print(f"⚠️ 권한 오류: Video Intelligence API가 프로젝트에서 활성화되지 않았을 수 있습니다.")
            print(f"   다음 명령어로 API를 활성화하세요:")
            print(f"   gcloud services enable videointelligence.googleapis.com --project={project_id}")
            
        except Exception as e:
            print(f"⚠️ API 호출 중 오류: {str(e)}")
            
    except Exception as e:
        print(f"❌ 클라이언트 초기화 실패: {str(e)}")
        print("\n해결 방법:")
        print("1. gcloud auth application-default login 실행")
        print("2. 또는 서비스 계정 키 파일을 생성하고 GOOGLE_APPLICATION_CREDENTIALS 환경변수 설정")
        return False
    
    return True

if __name__ == "__main__":
    success = test_video_intelligence_connection()
    sys.exit(0 if success else 1)