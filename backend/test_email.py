#!/usr/bin/env python3
"""
メール送信テストスクリプト
Gmail SMTPを使用してテストメールを送信
"""

import os
import sys
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

def test_email_with_gmail():
    """
    Gmailを使用したテストメール送信
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # 設定を確認
    print("=== メール設定確認 ===")
    print(f"SMTP_HOST: {os.getenv('SMTP_HOST', 'Not set')}")
    print(f"SMTP_PORT: {os.getenv('SMTP_PORT', 'Not set')}")
    print(f"SMTP_USER: {os.getenv('SMTP_USER', 'Not set')}")
    print(f"SMTP_PASSWORD: {'***' if os.getenv('SMTP_PASSWORD') else 'Not set'}")
    print(f"DEMO_MODE: {os.getenv('DEMO_MODE', 'Not set')}")
    print("")
    
    # Gmailの設定方法を表示
    if os.getenv('SMTP_USER') == 'your-email@gmail.com':
        print("⚠️  Gmail設定が必要です！")
        print("")
        print("=== Gmail設定方法 ===")
        print("1. Googleアカウントにログイン")
        print("2. https://myaccount.google.com/security にアクセス")
        print("3. '2段階認証プロセス'を有効にする")
        print("4. 'アプリパスワード'を生成")
        print("   - 'アプリを選択' → 'その他（カスタム名）'")
        print("   - 'video-accounting-app'などの名前を入力")
        print("   - 生成された16文字のパスワードをコピー")
        print("")
        print("5. .envファイルを更新:")
        print("   SMTP_USER=あなたのGmailアドレス")
        print("   SMTP_PASSWORD=生成した16文字のパスワード（スペースなし）")
        print("   FROM_EMAIL=あなたのGmailアドレス")
        print("   DEMO_MODE=false")
        print("")
        return
    
    # テストメール送信
    if os.getenv('DEMO_MODE') == 'true':
        print("ℹ️  DEMO_MODE=true のため、実際のメール送信はスキップされます")
        print("実際にメールを送信するには、.envファイルで DEMO_MODE=false に設定してください")
        return
    
    # 送信先メールアドレスを入力
    to_email = input("テストメールの送信先アドレスを入力してください: ").strip()
    if not to_email:
        print("メールアドレスが入力されていません")
        return
    
    try:
        # メッセージの作成
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "【テスト】動画会計アプリ - メール送信テスト"
        msg['From'] = f"動画会計アプリ <{os.getenv('FROM_EMAIL')}>"
        msg['To'] = to_email
        
        # HTMLコンテンツ
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                .container { max-width: 600px; margin: 0 auto; }
                .header { background: #667eea; color: white; padding: 20px; border-radius: 10px; }
                .content { background: #f8f9fa; padding: 20px; margin-top: 20px; border-radius: 10px; }
                .success { color: #28a745; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>メール送信テスト</h1>
                </div>
                <div class="content">
                    <p class="success">✅ メール送信が正常に動作しています！</p>
                    <p>このメールが届いていれば、メール設定は正しく構成されています。</p>
                    <p>パスワードリセット機能も正常に動作するはずです。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # テキストコンテンツ
        text_content = """
        メール送信テスト
        
        ✅ メール送信が正常に動作しています！
        
        このメールが届いていれば、メール設定は正しく構成されています。
        パスワードリセット機能も正常に動作するはずです。
        """
        
        part_text = MIMEText(text_content, 'plain', 'utf-8')
        part_html = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part_text)
        msg.attach(part_html)
        
        # SMTP接続と送信
        print(f"\n📧 {to_email} にテストメールを送信中...")
        
        with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
            server.send_message(msg)
        
        print("✅ メール送信成功！")
        print(f"   {to_email} の受信トレイを確認してください")
        print("   （迷惑メールフォルダも確認してください）")
        
    except Exception as e:
        print(f"❌ メール送信失敗: {e}")
        print("\n=== トラブルシューティング ===")
        print("1. Gmailの2段階認証が有効になっているか確認")
        print("2. アプリパスワードが正しく生成されているか確認")
        print("3. .envファイルの設定が正しいか確認")
        print("4. ファイアウォールやアンチウイルスソフトがSMTP通信をブロックしていないか確認")

if __name__ == "__main__":
    print("=== 動画会計アプリ - メール送信テスト ===\n")
    test_email_with_gmail()