#!/usr/bin/env python3
"""Gmail SMTP 테스트"""
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# backend 디렉토리 추가
sys.path.insert(0, '/Users/taehyeonglee/video-accounting-app/backend')

# .env 파일 직접 읽기
from dotenv import load_dotenv
load_dotenv('/Users/taehyeonglee/video-accounting-app/backend/.env')

# 설정 확인
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = "forone.video2@gmail.com"
smtp_password = "ujqbdsagmerfbnvp"
from_email = "forone.video2@gmail.com"

print("=" * 50)
print("Gmail SMTP 테스트")
print("=" * 50)
print(f"Host: {smtp_host}:{smtp_port}")
print(f"User: {smtp_user}")
print(f"Password: {'*' * 12}")
print()

try:
    print("1. SMTP 서버 연결 중...")
    server = smtplib.SMTP(smtp_host, smtp_port)
    
    print("2. TLS 시작...")
    server.starttls()
    
    print("3. 로그인 중...")
    server.login(smtp_user, smtp_password)
    
    print("✅ 로그인 성공!")
    
    # 테스트 메일 발송
    test_email = input("\n테스트 이메일 받을 주소 입력 (엔터=건너뛰기): ").strip()
    
    if test_email:
        print(f"\n{test_email}로 테스트 메일 발송 중...")
        
        msg = MIMEMultipart()
        msg['From'] = f"動画会計アプリ <{from_email}>"
        msg['To'] = test_email
        msg['Subject'] = "【テスト】Gmail SMTP 설정 성공!"
        
        body = """
        축하합니다! 🎉
        
        Gmail SMTP 설정이 성공적으로 완료되었습니다.
        이제 비밀번호 재설정 이메일을 발송할 수 있습니다.
        
        ---
        動画会計アプリ
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server.send_message(msg)
        print("✅ 테스트 메일 발송 성공!")
        print(f"   {test_email} 받은편지함을 확인하세요.")
    
    server.quit()
    print("\n🎉 모든 테스트 성공!")
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ 인증 실패: {e}")
    print("\n가능한 원인:")
    print("1. 앱 비밀번호가 올바르지 않음")
    print("2. 2단계 인증이 활성화되지 않음")
    print("3. 계정이 차단됨")
    
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")