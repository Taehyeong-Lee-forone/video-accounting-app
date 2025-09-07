#!/usr/bin/env python3
"""
メール送信機能テストスクリプト
使用方法: python test_email.py
"""
import os
import sys
from pathlib import Path

# バックエンドパスを追加
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
# 명시적으로 backend/.env 파일 로드
env_file = backend_path / ".env"
load_dotenv(env_file, override=True)
print(f"環境ファイル: {env_file}")

def test_smtp_connection():
    """SMTP接続をテスト"""
    import smtplib
    import os
    
    # 環境変数を再ロード
    load_dotenv(env_file, override=True)
    
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    print(f"📧 SMTP接続テスト")
    print(f"  Host: {smtp_host}:{smtp_port}")
    print(f"  User: {smtp_user}")
    print(f"  Password: {'*' * len(smtp_password) if smtp_password else '(未設定)'}")
    
    if not smtp_user or not smtp_password:
        print("❌ SMTP_USERまたはSMTP_PASSWORDが設定されていません")
        print("\n📝 設定方法:")
        print("1. backend/.envファイルを開く")
        print("2. SMTP_USER=your-email@gmail.com")
        print("3. SMTP_PASSWORD=your-app-password")
        return False
    
    try:
        print("\n接続中...")
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.quit()
        print("✅ SMTP接続成功！")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ 認証エラー")
        print("\n考えられる原因:")
        print("1. アプリパスワードが正しくない")
        print("2. 2段階認証が有効化されていない")
        print("3. Googleアカウントがブロックされている")
        return False
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

def test_send_email():
    """テストメール送信"""
    from services.email import email_service
    
    test_email = input("\nテストメールの送信先アドレスを入力してください: ").strip()
    if not test_email:
        print("キャンセルされました")
        return
    
    print(f"\n📤 {test_email} にテストメールを送信中...")
    
    # テストメール送信
    subject = "【テスト】動画会計アプリ - メール送信テスト"
    html_content = """
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>メール送信テスト成功！</h2>
        <p>このメールが届いていれば、メール送信機能は正常に動作しています。</p>
        <p style="color: #666; margin-top: 30px;">
            動画会計アプリ<br>
            自動送信メール
        </p>
    </body>
    </html>
    """
    text_content = "メール送信テスト成功！\n\nこのメールが届いていれば、メール送信機能は正常に動作しています。"
    
    success = email_service.send_email(test_email, subject, html_content, text_content)
    
    if success:
        print("✅ テストメール送信成功！")
        print(f"   {test_email} の受信箱を確認してください")
    else:
        print("❌ テストメール送信失敗")
        print("   backend/.envのSMTP設定を確認してください")

def test_password_reset_email():
    """パスワードリセットメールのテスト"""
    from services.email import email_service
    
    test_email = input("\nパスワードリセットメールの送信先アドレスを入力してください: ").strip()
    if not test_email:
        print("キャンセルされました")
        return
    
    print(f"\n📤 {test_email} にパスワードリセットメールを送信中...")
    
    # ダミートークンでテスト
    success = email_service.send_password_reset_email(
        to_email=test_email,
        reset_token="test-token-12345",
        username="テストユーザー"
    )
    
    if success:
        print("✅ パスワードリセットメール送信成功！")
        print(f"   {test_email} の受信箱を確認してください")
        print("   ※これはテストメールなので、リンクは機能しません")
    else:
        print("❌ パスワードリセットメール送信失敗")

if __name__ == "__main__":
    print("=" * 50)
    print("動画会計アプリ - メール機能テスト")
    print("=" * 50)
    
    # SMTP接続テスト
    if test_smtp_connection():
        print("\n" + "=" * 50)
        print("メニュー:")
        print("1. テストメールを送信")
        print("2. パスワードリセットメールをテスト")
        print("3. 終了")
        
        choice = input("\n選択してください (1-3): ").strip()
        
        if choice == "1":
            test_send_email()
        elif choice == "2":
            test_password_reset_email()
        else:
            print("終了します")
    else:
        print("\n⚠️  まず、backend/.envファイルのSMTP設定を完了してください")