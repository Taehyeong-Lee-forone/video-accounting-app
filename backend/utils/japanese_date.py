"""
Japanese Era (元号) to Gregorian year conversion utility
"""

import re
from datetime import datetime
from typing import Optional, Tuple

# Japanese Era definitions
JAPANESE_ERAS = {
    '令和': {'start': 2019, 'kanji': '令和', 'romaji': 'Reiwa', 'abbr': 'R'},
    '平成': {'start': 1989, 'end': 2019, 'kanji': '平成', 'romaji': 'Heisei', 'abbr': 'H'},
    '昭和': {'start': 1926, 'end': 1989, 'kanji': '昭和', 'romaji': 'Showa', 'abbr': 'S'},
    '大正': {'start': 1912, 'end': 1926, 'kanji': '大正', 'romaji': 'Taisho', 'abbr': 'T'},
    '明治': {'start': 1868, 'end': 1912, 'kanji': '明治', 'romaji': 'Meiji', 'abbr': 'M'},
}

def parse_japanese_date(date_str: str) -> Optional[datetime]:
    """
    Parse Japanese date string with era name to datetime object
    
    Examples:
        令和6年12月25日 -> 2024-12-25
        R6.12.25 -> 2024-12-25
        平成31年4月30日 -> 2019-04-30
        H31/4/30 -> 2019-04-30
        2025年2月7日 -> 2025-02-07
        7年2月7日 -> Assumes Reiwa 7 (2025-02-07)
        7月26日 -> Current year with month/day
    """
    if not date_str:
        return None
    
    # Clean the string
    date_str = date_str.strip()
    
    # Handle typos like "025年" -> "2025年"
    if re.match(r'^0\d{2}年', date_str):
        date_str = '2' + date_str
    
    # Pattern 1: Full format with kanji (令和6年12月25日)
    pattern1 = r'([令平昭大明][和成]?)(\d{1,2})[年](\d{1,2})[月](\d{1,2})[日]?'
    match1 = re.search(pattern1, date_str)
    
    if match1:
        era_char = match1.group(1)
        year_in_era = int(match1.group(2))
        month = int(match1.group(3))
        day = int(match1.group(4))
        
        # Find the era
        for era_name, era_info in JAPANESE_ERAS.items():
            if era_char[0] in era_name:
                gregorian_year = era_info['start'] + year_in_era - 1
                try:
                    return datetime(gregorian_year, month, day)
                except ValueError:
                    # Invalid date
                    return None
    
    # Pattern 2: Abbreviated format (R6.12.25 or R6/12/25)
    pattern2 = r'([RHSTM])(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{1,2})'
    match2 = re.search(pattern2, date_str.upper())
    
    if match2:
        era_abbr = match2.group(1)
        year_in_era = int(match2.group(2))
        month = int(match2.group(3))
        day = int(match2.group(4))
        
        # Find the era by abbreviation
        for era_name, era_info in JAPANESE_ERAS.items():
            if era_info['abbr'] == era_abbr:
                gregorian_year = era_info['start'] + year_in_era - 1
                try:
                    return datetime(gregorian_year, month, day)
                except ValueError:
                    # Invalid date
                    return None
    
    # Pattern 3: 元年 (first year of era)
    pattern3 = r'([令平昭大明][和成]?)元年(\d{1,2})[月](\d{1,2})[日]?'
    match3 = re.search(pattern3, date_str)
    
    if match3:
        era_char = match3.group(1)
        month = int(match3.group(2))
        day = int(match3.group(3))
        
        # Find the era
        for era_name, era_info in JAPANESE_ERAS.items():
            if era_char[0] in era_name:
                gregorian_year = era_info['start']  # 元年 = first year
                try:
                    return datetime(gregorian_year, month, day)
                except ValueError:
                    return None
    
    # Pattern 4: Year only (令和6年)
    pattern4 = r'([令平昭大明][和成]?)(\d{1,2})[年]'
    match4 = re.search(pattern4, date_str)
    
    if match4:
        era_char = match4.group(1)
        year_in_era = int(match4.group(2))
        
        # Find the era
        for era_name, era_info in JAPANESE_ERAS.items():
            if era_char[0] in era_name:
                gregorian_year = era_info['start'] + year_in_era - 1
                # Return January 1st of that year
                return datetime(gregorian_year, 1, 1)
    
    # Pattern 5: YYYY年MM月DD日 format (without era)
    pattern5 = r'(\d{4})[年](\d{1,2})[月](\d{1,2})[日]?'
    match5 = re.search(pattern5, date_str)
    
    if match5:
        year = int(match5.group(1))
        month = int(match5.group(2))
        day = int(match5.group(3))
        try:
            return datetime(year, month, day)
        except ValueError:
            return None
    
    # Pattern 6: YY年MM月DD日 (assumes current era - Reiwa)
    pattern6 = r'^(\d{1,2})[年](\d{1,2})[月](\d{1,2})[日]?$'
    match6 = re.search(pattern6, date_str)
    
    if match6:
        year_in_era = int(match6.group(1))
        month = int(match6.group(2))
        day = int(match6.group(3))
        # Assume Reiwa era for short year format
        gregorian_year = 2019 + year_in_era - 1  # Reiwa started in 2019
        try:
            return datetime(gregorian_year, month, day)
        except ValueError:
            return None
    
    # Pattern 7: MM月DD日 (month and day only - use current year)
    pattern7 = r'^(\d{1,2})[月](\d{1,2})[日]?$'
    match7 = re.search(pattern7, date_str)
    
    if match7:
        month = int(match7.group(1))
        day = int(match7.group(2))
        current_year = datetime.now().year
        try:
            return datetime(current_year, month, day)
        except ValueError:
            return None
    
    # If no Japanese era pattern found, try standard date parsing
    # Check for YYYY-MM-DD or YYYY/MM/DD format
    standard_pattern = r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})'
    standard_match = re.search(standard_pattern, date_str)
    
    if standard_match:
        year = int(standard_match.group(1))
        month = int(standard_match.group(2))
        day = int(standard_match.group(3))
        try:
            return datetime(year, month, day)
        except ValueError:
            return None
    
    return None

def convert_to_japanese_era(date: datetime) -> str:
    """
    Convert datetime to Japanese era format
    
    Example:
        2024-12-25 -> 令和6年12月25日
    """
    year = date.year
    
    # Find the appropriate era
    for era_name, era_info in JAPANESE_ERAS.items():
        if year >= era_info['start']:
            if 'end' not in era_info or year < era_info['end']:
                year_in_era = year - era_info['start'] + 1
                return f"{era_name}{year_in_era}年{date.month}月{date.day}日"
    
    # Fallback to standard format
    return date.strftime('%Y年%m月%d日')

def is_japanese_era_date(date_str: str) -> bool:
    """
    Check if the string contains Japanese era date
    """
    if not date_str:
        return False
    
    # Check for era names
    era_patterns = ['令和', '平成', '昭和', '大正', '明治', 'R', 'H', 'S', 'T', 'M']
    for pattern in era_patterns:
        if pattern in date_str.upper():
            # Also check for year marker
            if '年' in date_str or re.search(r'[RHSTM]\d', date_str.upper()):
                return True
    
    return False

# Test functions
if __name__ == "__main__":
    test_dates = [
        "令和6年12月25日",
        "R6.12.25",
        "平成31年4月30日",
        "H31/4/30",
        "昭和64年1月7日",
        "令和元年5月1日",
        "2024-12-25",
        "2024/12/25",
    ]
    
    for date_str in test_dates:
        result = parse_japanese_date(date_str)
        if result:
            print(f"{date_str} -> {result.strftime('%Y-%m-%d')}")
            # Convert back
            japanese = convert_to_japanese_era(result)
            print(f"  -> {japanese}")
        else:
            print(f"{date_str} -> Failed to parse")