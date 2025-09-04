"""
改善版OCRプロンプト - より正確な店舗名と日付の抽出
"""

IMPROVED_GEMINI_PROMPT = """あなたは日本の領収書/レシートの専門的な読取りアシスタントです。
画像から情報を正確に抽出して、以下のJSONを返してください。

【重要な識別ルール】
1. vendor（店舗名）: 領収書を「発行した」店舗・企業名
   - 領収書の上部にあるロゴや大きな文字の店舗名を優先
   - 「様」「御中」の前にある名前は宛名（購入者）なので除外
   - 住所・電話番号の近くにある店舗名を探す
   - 例: セブンイレブン、イオン、ローソン等

2. issue_date（発行日）: この領収書が発行された日付のみ
   - 「年月日」「発行日」「日付」「Date」と書かれた近くの日付
   - レジ番号や時刻の近くにある日付を優先
   - 他の領収書の日付と混同しない（この画像内の日付のみ）
   - 複数の日付がある場合は、レシート上部の日付を優先

3. recipient（宛名）: 領収書を「受け取る」人・企業名
   - 「様」「御中」の前にある名前
   - 手書きの場合が多い
   - 無記名の場合は null

【抽出フォーマット】
{
  "vendor": "発行元の店舗・企業名",
  "recipient": "宛名（様・御中の前の名前）またはnull",
  "document_type": "領収書|請求書|レシート|見積書|その他",
  "issue_date": "この画像内の発行日のみ（例: 2024年2月7日）",
  "currency": "JPY",
  "total": 税込総額（数値）,
  "subtotal": 小計（数値）,
  "tax": 消費税額（数値）,
  "tax_rate": 0.10|0.08|0|null,
  "line_items": [{"name":"商品名", "qty":数量, "unit_price":単価, "amount":金額}],
  "payment_method": "現金|クレジット|電子マネー|不明",
  "address": "発行元の住所",
  "phone": "発行元の電話番号",
  "memo": "その他の重要情報"
}

【注意事項】
- vendorとrecipientを混同しないこと
- 日付は必ずこの画像内に表示されているものだけを使用
- 金額は数値として返す
- 存在しない項目はnull

返答はJSONのみ。"""

def get_improved_prompt():
    """改善版プロンプトを返す"""
    return IMPROVED_GEMINI_PROMPT

def parse_vendor_from_ocr(ocr_text: str) -> dict:
    """
    OCRテキストから店舗名と宛名を分離して抽出
    """
    import re
    
    lines = ocr_text.split('\n')
    result = {
        'vendor': None,
        'recipient': None,
        'vendor_candidates': [],
        'recipient_candidates': []
    }
    
    # 宛名パターン（「様」「御中」の前）
    recipient_patterns = [
        r'(.+?)[様殿]',
        r'(.+?)御中',
        r'お客様：(.+)',
        r'宛名[：:]\s*(.+)'
    ]
    
    # 発行元パターン
    vendor_indicators = [
        # 店舗系
        r'(.*?店)',
        r'(.*?ストア)',
        r'(.*?マート)',
        r'(.*?スーパー)',
        r'(.*?センター)',
        # 企業系
        r'(株式会社.*)',
        r'(有限会社.*)',
        r'(合同会社.*)',
        r'(.*株式会社)',
        r'(.*\(株\))',
        r'(.*㈱)',
        # チェーン店
        r'(セブンイレブン.*)',
        r'(ファミリーマート.*)',
        r'(ローソン.*)',
        r'(イオン.*)',
    ]
    
    # 住所・電話番号の近くを優先
    address_pattern = r'〒?\d{3}-?\d{4}|.*[都道府県市区町村].*'
    phone_pattern = r'(TEL|Tel|電話|☎)[：:\s]*([\d\-]+)'
    
    # 各行を解析
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # 宛名チェック
        for pattern in recipient_patterns:
            match = re.search(pattern, line)
            if match:
                recipient = match.group(1).strip()
                if recipient and len(recipient) > 1:
                    result['recipient_candidates'].append((i, recipient))
        
        # 発行元チェック（最初の10行を重点的に）
        if i < 10:
            # 住所や電話番号が近くにある場合は優先度高
            priority = 1
            if i < len(lines) - 1:
                next_line = lines[i + 1] if i < len(lines) - 1 else ""
                if re.search(address_pattern, next_line) or re.search(phone_pattern, next_line):
                    priority = 3
            
            # 店舗名パターンマッチ
            for pattern in vendor_indicators:
                match = re.search(pattern, line)
                if match:
                    vendor = match.group(1).strip()
                    if vendor and len(vendor) > 1:
                        result['vendor_candidates'].append((priority, i, vendor))
            
            # パターンに合わない場合でも、上部の大きなテキストは候補
            if i < 3 and len(line) > 2 and not re.match(r'^[\d\s\-\/\.:]+$', line):
                if '様' not in line and '御中' not in line:
                    result['vendor_candidates'].append((0, i, line))
    
    # 最適な候補を選択
    if result['vendor_candidates']:
        # 優先度とインデックスでソート
        result['vendor_candidates'].sort(key=lambda x: (-x[0], x[1]))
        result['vendor'] = result['vendor_candidates'][0][2]
    
    if result['recipient_candidates']:
        # 最初に見つかった宛名を使用
        result['recipient'] = result['recipient_candidates'][0][1]
    
    return result

def extract_date_from_current_frame_only(ocr_text: str, frame_index: int = None) -> str:
    """
    現在のフレームからのみ日付を抽出（他のフレームの日付と混同しない）
    """
    import re
    from datetime import datetime
    
    # 日付パターン（優先順位順）
    date_patterns = [
        # 完全な日付形式
        (r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日]?', 'full'),
        (r'令和(\d{1,2})年(\d{1,2})月(\d{1,2})日', 'reiwa'),
        (r'R(\d{1,2})[\./-](\d{1,2})[\./-](\d{1,2})', 'reiwa_short'),
        (r'平成(\d{1,2})年(\d{1,2})月(\d{1,2})日', 'heisei'),
        (r'H(\d{1,2})[\./-](\d{1,2})[\./-](\d{1,2})', 'heisei_short'),
        # 月日のみ（年は現在年を使用）
        (r'(\d{1,2})[月/-](\d{1,2})[日]?', 'month_day'),
    ]
    
    lines = ocr_text.split('\n')
    found_dates = []
    
    # 日付キーワードの近くを優先
    date_keywords = ['日付', '発行日', 'Date', '年月日', '取引日']
    
    for i, line in enumerate(lines[:20]):  # 最初の20行のみチェック
        line = line.strip()
        
        # 日付キーワードが含まれる行は優先度高
        priority = 2 if any(kw in line for kw in date_keywords) else 1
        
        # 上部（最初の5行）の日付は優先度高
        if i < 5:
            priority += 1
        
        for pattern, date_type in date_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                try:
                    if date_type == 'full':
                        year, month, day = match.groups()
                        year = int(year)
                        month = int(month)
                        day = int(day)
                    elif date_type == 'reiwa':
                        r_year, month, day = match.groups()
                        year = 2018 + int(r_year)  # 令和元年 = 2019
                        month = int(month)
                        day = int(day)
                    elif date_type == 'reiwa_short':
                        r_year, month, day = match.groups()
                        year = 2018 + int(r_year)
                        month = int(month)
                        day = int(day)
                    elif date_type == 'heisei':
                        h_year, month, day = match.groups()
                        year = 1988 + int(h_year)  # 平成元年 = 1989
                        month = int(month)
                        day = int(day)
                    elif date_type == 'heisei_short':
                        h_year, month, day = match.groups()
                        year = 1988 + int(h_year)
                        month = int(month)
                        day = int(day)
                    elif date_type == 'month_day':
                        month, day = match.groups()
                        year = datetime.now().year
                        month = int(month)
                        day = int(day)
                    else:
                        continue
                    
                    # 妥当性チェック
                    if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        date_str = f"{year}年{month}月{day}日"
                        found_dates.append((priority, i, date_str, match.start()))
                        
                except (ValueError, IndexError):
                    continue
    
    # 最も優先度の高い日付を選択
    if found_dates:
        # 優先度（高い方が良い）、行番号（小さい方が良い）、位置（小さい方が良い）でソート
        found_dates.sort(key=lambda x: (-x[0], x[1], x[3]))
        return found_dates[0][2]
    
    return None