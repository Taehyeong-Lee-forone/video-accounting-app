import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re
from sqlalchemy.orm import Session
from models import Vendor, Account, Rule, JournalEntry, Receipt
from schemas import JournalEntryCreate, PaymentMethod

logger = logging.getLogger(__name__)

class JournalGenerator:
    """仕訳自動生成サービス"""
    
    def __init__(self, db: Session):
        self.db = db
        self._load_default_accounts()
    
    def _load_default_accounts(self):
        """デフォルト勘定科目の初期化"""
        self.default_accounts = {
            'expenses': {
                '旅費交通費': '5110',
                '交際費': '5120',
                '会議費': '5130',
                '消耗品費': '5140',
                '通信費': '5150',
                '水道光熱費': '5160',
                '地代家賃': '5170',
                '支払手数料': '5180',
                '雑費': '5190',
            },
            'assets': {
                '現金': '1110',
                '普通預金': '1120',
                '売掛金': '1130',
                '立替金': '1140',
                '前払費用': '1150',
            },
            'liabilities': {
                '買掛金': '2110',
                '未払金': '2120',
                '未払費用': '2130',
                '預り金': '2140',
            },
            'tax': {
                '仮払消費税等': '1310',
                '仮受消費税等': '2310',
            }
        }
    
    def generate_journal_entries(self, receipt: Receipt) -> List[JournalEntryCreate]:
        """領収書から仕訳を自動生成"""
        entries = []
        
        # ベンダーマスタから勘定科目を取得
        vendor = self._get_vendor(receipt.vendor_norm)
        
        # 借方・貸方勘定の決定 (None を返さないように保証)
        debit_account = self._determine_debit_account(receipt, vendor) or self.default_accounts['expenses']['雑費']
        credit_account = self._determine_credit_account(receipt, vendor) or self.default_accounts['liabilities']['未払金']
        
        # 税額計算
        tax_amount, tax_account = self._calculate_tax(receipt)
        
        if receipt.total:
            # 1行で簡素化された仕訳
            entries.append(JournalEntryCreate(
                receipt_id=receipt.id,
                video_id=receipt.video_id,
                time_ms=self._get_frame_time(receipt),
                debit_account=debit_account or self.default_accounts['expenses']['雑費'],
                credit_account=credit_account or self.default_accounts['liabilities']['未払金'],
                debit_amount=receipt.total,
                credit_amount=receipt.total,
                tax_account=tax_account if tax_amount > 0 else None,
                tax_amount=tax_amount if tax_amount > 0 else None,
                memo=receipt.vendor  # 簡単なメモのみ
            ))
        
        return entries
    
    def _get_vendor(self, vendor_norm: str) -> Optional[Vendor]:
        """ベンダーマスタから検索"""
        if not vendor_norm:
            return None
        
        return self.db.query(Vendor).filter(
            Vendor.name_norm == vendor_norm
        ).first()
    
    def _determine_debit_account(self, receipt: Receipt, vendor: Optional[Vendor]) -> str:
        """借方勘定科目の決定"""
        # 1. ベンダーマスタ優先
        if vendor and vendor.default_debit_account:
            return vendor.default_debit_account
        
        # 2. ルールベース判定
        rules = self.db.query(Rule).filter(
            Rule.is_active == True
        ).order_by(Rule.priority.desc()).all()
        
        for rule in rules:
            if self._match_rule(rule, receipt):
                if rule.debit_account:
                    return rule.debit_account
        
        # 3. 汎用ルール（ベンダー名から推測）
        if receipt.vendor_norm:
            vendor_lower = receipt.vendor_norm.lower()
            
            # 交通費
            if any(keyword in vendor_lower for keyword in ['jr', 'taxi', 'タクシー', '鉄道', 'バス']):
                return self.default_accounts['expenses']['旅費交通費']
            
            # 飲食費
            if any(keyword in vendor_lower for keyword in ['スタバ', 'starbucks', 'カフェ', 'レストラン']):
                return self.default_accounts['expenses']['会議費']
            
            # ガソリン代
            if any(keyword in vendor_lower for keyword in ['eneos', 'エネオス', 'shell', 'コスモ']):
                return self.default_accounts['expenses']['旅費交通費']
            
            # コンビニ・小売
            if any(keyword in vendor_lower for keyword in ['セブン', 'ローソン', 'ファミリー', 'amazon']):
                return self.default_accounts['expenses']['消耗品費']
        
        # デフォルト
        return self.default_accounts['expenses']['雑費']
    
    def _determine_credit_account(self, receipt: Receipt, vendor: Optional[Vendor]) -> str:
        """貸方勘定科目の決定"""
        # 1. ベンダーマスタ優先
        if vendor and vendor.default_credit_account:
            return vendor.default_credit_account
        
        # 2. 支払方法から判定 (文字列比較)
        if receipt.payment_method:
            payment_method_lower = receipt.payment_method.lower()
            # 現金
            if any(keyword in payment_method_lower for keyword in ['現金', 'cash', '現']):
                return self.default_accounts['assets']['現金']
            # クレジットカード
            elif any(keyword in payment_method_lower for keyword in ['クレジット', 'credit', 'カード', 'card', '信用']):
                return self.default_accounts['liabilities']['未払金']
            # 電子マネー
            elif any(keyword in payment_method_lower for keyword in ['電子マネー', 'emoney', 'suica', 'pasmo', 'paypay', '電子']):
                return self.default_accounts['assets']['普通預金']
        
        # 3. デフォルト
        return self.default_accounts['liabilities']['未払金']
    
    def _calculate_tax(self, receipt: Receipt) -> Tuple[float, str]:
        """税額計算"""
        tax_amount = 0
        tax_account = self.default_accounts['tax']['仮払消費税等']
        
        if receipt.tax_rate and receipt.total:
            if receipt.tax:
                # 税額が明示されている場合
                tax_amount = receipt.tax
            else:
                # 内税計算
                tax_amount = round(receipt.total * receipt.tax_rate / (1 + receipt.tax_rate))
        
        return tax_amount, tax_account
    
    def _match_rule(self, rule: Rule, receipt: Receipt) -> bool:
        """ルールマッチング"""
        try:
            pattern = re.compile(rule.pattern, re.IGNORECASE)
            
            if rule.pattern_type == 'vendor':
                return bool(pattern.search(receipt.vendor or ''))
            elif rule.pattern_type == 'item':
                # 品目での判定（将来拡張用）
                return False
            elif rule.pattern_type == 'amount_range':
                # 金額範囲での判定
                if receipt.total:
                    return pattern.search(str(receipt.total))
            
            # デフォルトはベンダー名で判定
            return bool(pattern.search(receipt.vendor or ''))
            
        except Exception as e:
            logger.error(f"ルールマッチングエラー: {e}")
            return False
    
    def _get_frame_time(self, receipt: Receipt) -> int:
        """レシートのベストフレーム時刻を取得"""
        if receipt.best_frame:
            return receipt.best_frame.time_ms
        return 0
    
    def apply_confirmation(self, journal_id: int, confirmed_by: str, status: str = 'confirmed') -> JournalEntry:
        """仕訳の承認処理"""
        journal = self.db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
        
        if not journal:
            raise ValueError(f"仕訳ID {journal_id} が見つかりません")
        
        journal.status = status
        journal.confirmed_by = confirmed_by
        journal.confirmed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(journal)
        
        return journal