"""
Vendor名の正規化ユーティリティ
同一動画内で異なるvendor名が検出された場合に統一する
"""

from typing import List, Dict, Optional
from collections import Counter
import re
from difflib import SequenceMatcher

class VendorNormalizer:
    """Vendor名の正規化クラス"""
    
    def __init__(self):
        # 一般的な領収書のノイズワード
        self.noise_words = [
            '領収書', '領収証', 'レシート', 'RECEIPT',
            '御買上票', '売上票', 'お買い上げ',
            '計算書', '請求書', '納品書'
        ]
        
    def normalize_vendor_names(self, receipts: List[Dict]) -> List[Dict]:
        """
        複数の領収書データのvendor名を正規化
        最も頻出するvendor名または最も具体的な名前を採用
        """
        if not receipts:
            return receipts
            
        # vendor名を収集（ノイズワードを除外）
        vendor_candidates = []
        for receipt in receipts:
            vendor = receipt.get('vendor', '').strip()
            if vendor and not self._is_noise_vendor(vendor):
                vendor_candidates.append(vendor)
        
        # 最適なvendor名を決定
        best_vendor = self._find_best_vendor(vendor_candidates)
        
        # 全ての領収書のvendor名を統一
        if best_vendor:
            for receipt in receipts:
                current_vendor = receipt.get('vendor', '').strip()
                # ノイズワードまたは空の場合のみ置換
                if not current_vendor or self._is_noise_vendor(current_vendor):
                    receipt['vendor'] = best_vendor
                # 類似度が高い場合も統一
                elif self._calculate_similarity(current_vendor, best_vendor) > 0.7:
                    receipt['vendor'] = best_vendor
        
        return receipts
    
    def _is_noise_vendor(self, vendor: str) -> bool:
        """vendor名がノイズワードかどうか判定"""
        vendor_lower = vendor.lower()
        for noise in self.noise_words:
            if noise.lower() in vendor_lower:
                return True
        return False
    
    def _find_best_vendor(self, vendors: List[str]) -> Optional[str]:
        """最適なvendor名を決定"""
        if not vendors:
            return None
            
        # 頻度でカウント
        vendor_counts = Counter(vendors)
        
        # 最頻出のvendor名を取得
        most_common = vendor_counts.most_common(3)
        
        if not most_common:
            return None
            
        # 同じ頻度の場合、より具体的な（長い）名前を選択
        best_vendor = most_common[0][0]
        best_count = most_common[0][1]
        
        for vendor, count in most_common:
            # 同じ頻度でより長い名前があれば採用
            if count == best_count and len(vendor) > len(best_vendor):
                # 「様」が付いている方を優先
                if '様' in vendor and '様' not in best_vendor:
                    best_vendor = vendor
                elif '様' not in vendor and '様' not in best_vendor:
                    best_vendor = vendor
        
        return best_vendor
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """2つの文字列の類似度を計算"""
        # 基本的な前処理
        str1 = self._normalize_string(str1)
        str2 = self._normalize_string(str2)
        
        # SequenceMatcherで類似度計算
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _normalize_string(self, s: str) -> str:
        """文字列の正規化（比較用）"""
        # 空白削除
        s = re.sub(r'\s+', '', s)
        # 記号を統一
        s = s.replace('（', '(').replace('）', ')')
        s = s.replace('株式会社', '㈱')
        # 小文字化
        return s.lower()
    
    def merge_similar_vendors(self, vendors: List[str], threshold: float = 0.8) -> Dict[str, str]:
        """
        類似するvendor名をマージするためのマッピングを作成
        
        Args:
            vendors: vendor名のリスト
            threshold: 類似度の閾値（0-1）
        
        Returns:
            元のvendor名から統一vendor名へのマッピング
        """
        mapping = {}
        processed = set()
        
        for i, vendor1 in enumerate(vendors):
            if vendor1 in processed:
                continue
                
            similar_vendors = [vendor1]
            
            for vendor2 in vendors[i+1:]:
                if vendor2 not in processed:
                    similarity = self._calculate_similarity(vendor1, vendor2)
                    if similarity >= threshold:
                        similar_vendors.append(vendor2)
                        processed.add(vendor2)
            
            # 最も長い/具体的なvendor名を採用
            best_vendor = max(similar_vendors, key=lambda x: (len(x), '様' in x))
            
            for vendor in similar_vendors:
                mapping[vendor] = best_vendor
        
        return mapping