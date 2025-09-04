#!/usr/bin/env python3
"""
日付抽出ロジックのテストスクリプト
"""

import re
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_date_extraction():
    """日付抽出のテストケース"""
    
    # テストケース
    test_cases = [
        ("6年11月26日", "令和6年11月26日"),  # 省略形式
        ("令和6年12月25日", "令和6年12月25日"),  # 完全形式
        ("R6.12.25", "R6.12.25"),  # R形式
        ("2024年12月25日", "2024年12月25日"),  # 西暦
        ("2024-12-25", "2024-12-25"),  # ISO形式
        ("20241225", "20241225"),  # 8桁数字
        ("7年1月5日", None),  # 未来の令和年（無効）
        ("99年12月31日", None),  # 無効な年
    ]
    
    # 日付パターン（vision_ocr.pyと同じ）
    patterns = [
        # 完全な日付形式（優先）
        r'(令和\d+年\d{1,2}月\d{1,2}日)',  # 令和6年12月25日
        r'(令和元年\d{1,2}月\d{1,2}日)',    # 令和元年
        r'(平成\d+年\d{1,2}月\d{1,2}日)',  # 平成31年4月30日
        r'(R\d+[\.\/\-]\d{1,2}[\.\/\-]\d{1,2})',  # R6.12.25, R6/12/25
        r'(H\d+[\.\/\-]\d{1,2}[\.\/\-]\d{1,2})',  # H31.4.30
        r'(\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2}[日]?)',  # 2024年12月25日, 2024/12/25
        r'(\d{4}-\d{2}-\d{2})',            # 2024-12-25
        r'(20\d{2}\d{2}\d{2})',            # 20241225（年が明確な8桁のみ）
        # 省略形式（令和を仮定）
        r'(\d{1}年\d{1,2}月\d{1,2}日)',    # 6年11月26日 → 令和6年として解釈
    ]
    
    current_year = datetime.now().year
    current_reiwa = current_year - 2018  # 令和元年 = 2019
    
    print("=" * 60)
    print("日付抽出テスト")
    print("=" * 60)
    
    for test_input, expected in test_cases:
        found = None
        normalized = None
        
        for pattern in patterns:
            match = re.search(pattern, test_input)
            if match:
                found = match.group(1)
                
                # 正規化処理
                if '令和' in found:
                    normalized = found
                elif 'R' in found and re.match(r'R\d+', found):
                    normalized = found
                elif re.match(r'\d{4}[年/-]', found):
                    year_match = re.search(r'(20\d{2})', found)
                    if year_match:
                        year = int(year_match.group(1))
                        if 2020 <= year <= 2025:
                            normalized = found
                elif re.match(r'\d{1}年\d{1,2}月\d{1,2}日', found):
                    # 省略形式を令和として解釈
                    m = re.match(r'(\d{1})年(\d{1,2})月(\d{1,2})日', found)
                    if m:
                        year_digit = int(m.group(1))
                        month = int(m.group(2))
                        day = int(m.group(3))
                        if 1 <= year_digit <= current_reiwa and 1 <= month <= 12 and 1 <= day <= 31:
                            normalized = f"令和{year_digit}年{month}月{day}日"
                elif re.match(r'20\d{6}', found):
                    year = int(found[0:4])
                    month = int(found[4:6])
                    day = int(found[6:8])
                    if 2020 <= year <= 2025 and 1 <= month <= 12 and 1 <= day <= 31:
                        normalized = found
                else:
                    normalized = found
                
                break
        
        # 結果表示
        status = "✅" if normalized == expected else "❌"
        print(f"{status} 入力: '{test_input}'")
        print(f"   期待: '{expected}'")
        print(f"   結果: '{normalized}'")
        print()
    
    # 実際のOCRテキストでテスト
    print("\n" + "=" * 60)
    print("実際のOCRテキスト例")
    print("=" * 60)
    
    sample_text = """
太郎商店様
船橋市市場1-1-1
6年11月26日
合計金額 5,616円
"""
    
    lines = sample_text.strip().split('\n')
    found_dates = []
    
    for i, line in enumerate(lines):
        for pattern in patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                date_str = match if isinstance(match, str) else match[0]
                if re.match(r'\d{1}年\d{1,2}月\d{1,2}日', date_str):
                    # 省略形式を令和として解釈
                    m = re.match(r'(\d{1})年(\d{1,2})月(\d{1,2})日', date_str)
                    if m:
                        year_digit = int(m.group(1))
                        month = int(m.group(2))
                        day = int(m.group(3))
                        if 1 <= year_digit <= current_reiwa and 1 <= month <= 12 and 1 <= day <= 31:
                            normalized = f"令和{year_digit}年{month}月{day}日"
                            found_dates.append((line.strip(), date_str, normalized))
    
    if found_dates:
        print("見つかった日付:")
        for line_text, original, normalized in found_dates:
            print(f"  行: '{line_text}'")
            print(f"  元: '{original}' → 正規化: '{normalized}'")
    else:
        print("日付が見つかりませんでした")

if __name__ == "__main__":
    test_date_extraction()