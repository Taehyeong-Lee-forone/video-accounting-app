#!/usr/bin/env python3
"""
Gmail 메일 설정 도우미
"""

import os
import sys
import getpass
from dotenv import load_dotenv, set_key

def setup_gmail():
    """Gmail 설정을 대화형으로 구성"""
    
    print("=== Gmail 메일 송신 설정 ===\n")
    print("이 도우미는 Gmail을 통한 메일 송신을 설정합니다.")
    print("먼저 Gmail 앱 패스워드가 필요합니다.\n")
    
    print("📋 앱 패스워드 생성 방법:")
    print("1. https://myaccount.google.com/security 접속")
    print("2. 2단계 인증 활성화")
    print("3. '앱 패스워드' 생성")
    print("4. 16자리 패스워드 복사\n")
    
    # 현재 설정 확인
    env_path = ".env"
    load_dotenv(env_path)
    
    current_user = os.getenv("SMTP_USER", "")
    if current_user and current_user != "your-email@gmail.com":
        use_current = input(f"현재 설정된 이메일: {current_user}\n이 설정을 유지하시겠습니까? (y/n): ")
        if use_current.lower() != 'y':
            current_user = ""
    else:
        current_user = ""
    
    # Gmail 주소 입력
    if not current_user:
        gmail_address = input("Gmail 주소를 입력하세요: ").strip()
        if not gmail_address or "@gmail.com" not in gmail_address:
            print("❌ 올바른 Gmail 주소를 입력하세요.")
            return False
    else:
        gmail_address = current_user
    
    # 앱 패스워드 입력
    print("\n앱 패스워드를 입력하세요 (16자리, 공백 제거):")
    app_password = getpass.getpass("패스워드: ").strip().replace(" ", "")
    
    if len(app_password) != 16:
        print(f"❌ 앱 패스워드는 16자리여야 합니다. (입력된 길이: {len(app_password)})")
        return False
    
    # 설정 저장 확인
    print("\n다음 설정을 저장합니다:")
    print(f"  SMTP_USER: {gmail_address}")
    print(f"  SMTP_PASSWORD: {'*' * 16}")
    print(f"  FROM_EMAIL: {gmail_address}")
    print(f"  DEMO_MODE: false")
    
    confirm = input("\n계속하시겠습니까? (y/n): ")
    if confirm.lower() != 'y':
        print("취소되었습니다.")
        return False
    
    # .env 파일 업데이트
    try:
        set_key(env_path, "SMTP_USER", gmail_address)
        set_key(env_path, "SMTP_PASSWORD", app_password)
        set_key(env_path, "FROM_EMAIL", gmail_address)
        set_key(env_path, "DEMO_MODE", "false")
        
        print("\n✅ 설정이 저장되었습니다!")
        
        # 테스트 여부 확인
        test_now = input("\n지금 테스트 메일을 보내시겠습니까? (y/n): ")
        if test_now.lower() == 'y':
            # test_email.py 실행
            import subprocess
            subprocess.run([sys.executable, "test_email.py"])
        else:
            print("\n나중에 다음 명령으로 테스트할 수 있습니다:")
            print("  python3 test_email.py")
        
        return True
        
    except Exception as e:
        print(f"❌ 설정 저장 실패: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print(" Gmail 메일 송신 설정 도우미")
    print("=" * 50 + "\n")
    
    success = setup_gmail()
    
    if success:
        print("\n🎉 설정 완료!")
        print("이제 패스워드 리셋 기능이 정상 작동합니다.")
    else:
        print("\n설정이 완료되지 않았습니다.")
        print("GMAIL_SETUP_GUIDE.md 파일을 참고하여 수동으로 설정하세요.")