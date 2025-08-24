"""
영수증 텍스트 파싱 유틸리티
더 정확한 금액 추출을 위한 고급 파서
"""

import re
from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ReceiptParser:
    """
    # 영수증 텍스트를 정확하게 파싱하는 유틸리티
    """
    
    def __init__(self):
        # 금액 패턴 정의 (더 정확한 패턴)
        self.amount_pattern = re.compile(
            r'[¥￥]?([\d]{1,3}(?:[,，][\d]{3})*)[円]?',
            re.IGNORECASE
        )
        
    def extract_all_amounts(self, text: str) -> List[float]:
        """
        # テキストからすべての金額を抽出
        텍스트에서 모든 금액 추출
        """
        amounts = []
        
        # 더 포괄적인 패턴들
        patterns = [
            r'[¥￥]([\d,]+)',  # ¥1,000
            r'([\d,]+)[円]',   # 1000円
            r'([\d,]+)(?=\s*円)',  # 1000 円
            r'(?:合計|小計|税込|税抜|計|総計|お預り|現金)[\s:：]*([\d,]+)',  # 합계: 1000
            r'^\s*([\d,]+)\s*$',  # 독립된 숫자 라인
            r'(?<!\d\.)(?<!0\.)([\d]{3,})(?![\d])',  # 3자리 이상 숫자 (소수점 제외)
        ]
        
        for pattern in patterns:
            if '^\s*' in pattern:
                # 멀티라인 매칭이 필요한 패턴
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            else:
                matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # 숫자만 추출
                amount_str = re.sub(r'[,，]', '', match)
                try:
                    amount = float(amount_str)
                    if 10 <= amount <= 999999:  # 현실적인 금액 범위
                        amounts.append(amount)
                except:
                    continue
                    
        return sorted(set(amounts))  # 중복 제거하고 정렬
    
    def find_total_amount(self, text: str) -> Optional[float]:
        """
        # 税込合計金額を見つける
        세금 포함 총액 찾기
        """
        lines = text.split('\n')
        amounts_with_context = []
        
        # 먼저 합계 키워드가 있는 라인과 다음 라인 체크
        for i, line in enumerate(lines):
            if any(word in line for word in ['合計金額', '合計', '総計', '税込合計', '税込']):
                # 같은 라인에 금액이 있는지 확인
                amounts = self.extract_all_amounts(line)
                if amounts:
                    for amount in amounts:
                        amounts_with_context.append((amount, 300, f"합계라인: {line[:30]}"))
                # 다음 라인에 금액이 있는지 확인
                elif i + 1 < len(lines):
                    next_line = lines[i + 1]
                    amounts = self.extract_all_amounts(next_line)
                    if amounts:
                        for amount in amounts:
                            amounts_with_context.append((amount, 280, f"합계다음: {next_line[:30]}"))
        
        # 일반적인 패턴 검색
        for i, line in enumerate(lines):
            # 금액 찾기
            amounts = self.extract_all_amounts(line)
            if not amounts:
                continue
                
            # 주변 문맥 확인
            context = ' '.join(lines[max(0, i-1):min(len(lines), i+2)])
            context_lower = context.lower()
            
            for amount in amounts:
                score = 0
                
                # 税込 관련 키워드
                if any(word in context for word in ['税込', '(税込)', '税込合計', '税込計']):
                    score += 200
                
                # 合計 관련 키워드 (税込이 없어도 합계는 보통 税込)
                if '合計' in line and '税抜' not in line and '小計' not in line:
                    score += 150
                elif any(word in context for word in ['総計', 'お会計', 'お買上計']):
                    score += 100
                    
                # お預り는 받은 금액이지 합계가 아님 (감점)
                if 'お預' in context or '預り' in context:
                    score -= 50
                    
                # 現金도 받은 금액 (라인 위치로 판단)
                if '現金' in context and i < len(lines) - 3:  # 마지막 부분이 아니면
                    score += 10
                elif '現金' in context:  # 마지막 부분이면 받은 금액
                    score -= 30
                    
                # 税抜 키워드가 있으면 감점
                if any(word in context for word in ['税抜', '小計', '税別']):
                    score -= 100
                    
                # 消費税 라인이면 감점
                if '消費税' in line and '合計' not in line:
                    score -= 100
                    
                amounts_with_context.append((amount, score, context[:50]))
        
        # 점수순 정렬
        amounts_with_context.sort(key=lambda x: (-x[1], -x[0]))  # 점수 높은순, 금액 큰순
        
        if amounts_with_context:
            best = amounts_with_context[0]
            logger.debug(f"Best total candidate: {best[0]} (score: {best[1]}, context: {best[2]})")
            
            # 점수가 양수이거나, 점수가 같으면 가장 큰 금액 선택
            if best[1] > 0:
                return best[0]
            else:
                # 명확한 税込 키워드가 없으면 가장 큰 금액을 税込으로 추정
                all_amounts = self.extract_all_amounts(text)
                if all_amounts:
                    return max(all_amounts)
                    
        return None
    
    def find_tax_amount(self, text: str, total: Optional[float] = None) -> Optional[float]:
        """
        # 消費税金額を見つける
        소비세 금액 찾기
        """
        lines = text.split('\n')
        tax_candidates = []
        
        for i, line in enumerate(lines):
            # 消費税 키워드가 있는 라인
            if any(word in line for word in ['消費税', '内税', '外税', '税', '内消費税']):
                amounts = self.extract_all_amounts(line)
                
                for amount in amounts:
                    # 세금은 보통 총액의 20% 이하
                    if total and amount > total * 0.2:
                        continue
                        
                    # 8% 또는 10% 세율에 해당하는지 확인
                    if total:
                        rate = amount / total
                        if 0.06 <= rate <= 0.12:  # 6%~12% 범위
                            tax_candidates.append(amount)
                    elif amount < 10000:  # 세금은 보통 10000엔 이하
                        tax_candidates.append(amount)
        
        if tax_candidates:
            # 가장 그럴듯한 세금 선택
            return tax_candidates[0]
            
        # 세금이 명시되지 않은 경우, total에서 역산
        if total:
            # 10% 세율 가정
            return round(total - (total / 1.1), 2)
            
        return None
    
    def parse_receipt(self, text: str) -> Dict[str, Optional[float]]:
        """
        # レシートテキストを解析
        영수증 텍스트 종합 분석
        """
        # 1. 税込 총액 찾기
        total = self.find_total_amount(text)
        
        # 2. 세금 찾기
        tax = self.find_tax_amount(text, total)
        
        # 3. 税抜 금액 계산
        if total and tax:
            subtotal = total - tax
        elif total:
            # 세금이 없으면 10% 세율로 역산
            subtotal = round(total / 1.1, 2)
            tax = total - subtotal
        else:
            subtotal = None
            
        # 4. 검증: total이 없거나 너무 작으면 다시 계산
        if not total or total < 100:
            all_amounts = self.extract_all_amounts(text)
            if all_amounts:
                # 가장 큰 금액을 total로
                total = max(all_amounts)
                # 10% 세율로 세금 계산
                subtotal = round(total / 1.1, 2)
                tax = total - subtotal
        
        return {
            'total': total,
            'subtotal': subtotal,
            'tax': tax,
            'tax_rate': round(tax / total, 3) if total and tax else 0.1
        }