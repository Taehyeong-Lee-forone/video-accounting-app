"""
Google Cloud Vision APIを使用したレシートOCRサービス
JSONキーなしでgcloud CLIまたはWorkload Identity使用
"""
import os
import logging
import re
import json
from typing import Dict, Any, Optional
from datetime import datetime
from google.cloud import vision
from google.api_core import exceptions
from PIL import Image
import io

logger = logging.getLogger(__name__)

class VisionOCRService:
    def __init__(self):
        """
        Vision APIクライアント初期化
        - ローカル: gcloud auth application-default login使用
        - Cloud Run: Workload Identity自動使用
        - Railway/Render: Base64エンコードされたJSONキー使用
        """
        try:
            # 環境変数からBase64エンコードされたJSONキーを確認
            import base64
            import tempfile
            from google.oauth2 import service_account
            
            credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
            
            if credentials_json:
                # Base64デコードしてJSONキーを復元
                credentials_data = json.loads(base64.b64decode(credentials_json))
                
                # サービスアカウント認証情報を作成
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_data,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                
                # 認証情報を使用してクライアント初期化
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("Vision API client initialized with service account credentials")
            else:
                # JSONキーなしでデフォルト認証使用
                self.client = vision.ImageAnnotatorClient()
                logger.info("Vision API client initialized with default credentials")
                
        except Exception as e:
            logger.error(f"Failed to initialize Vision API client: {e}")
            logger.info("Please run: gcloud auth application-default login or set GOOGLE_APPLICATION_CREDENTIALS_JSON")
            self.client = None
    
    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """画像からテキスト抽出（OCR）"""
        if not self.client:
            raise Exception("Vision API client not initialized")
        
        try:
            # 画像ファイル読み込み
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            
            # Document Text Detection使用（レシートにより適合）
            # 日本語を最優先に設定し、OCR精度向上
            response = self.client.document_text_detection(
                image=image,
                image_context={
                    'language_hints': ['ja', 'ja-JP', 'en'],  # 日本語優先
                    'text_detection_params': {
                        'enable_text_detection_confidence_score': True
                    }
                }
            )
            
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
            
            # 全体テキストと構造化されたデータを返す
            full_text = response.full_text_annotation.text if response.full_text_annotation else ""
            
            # テキストブロックごとに整理
            blocks = []
            if response.full_text_annotation:
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        block_text = ""
                        for paragraph in block.paragraphs:
                            for word in paragraph.words:
                                word_text = ''.join([symbol.text for symbol in word.symbols])
                                block_text += word_text + " "
                        blocks.append({
                            'text': block_text.strip(),
                            'confidence': block.confidence
                        })
            
            return {
                'full_text': full_text,
                'blocks': blocks,
                'raw_response': response
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    def parse_receipt_data(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """OCR結果からレシートデータをパース"""
        full_text = ocr_result.get('full_text', '')
        
        # 고급 파서 사용
        from utils.receipt_parser import ReceiptParser
        parser = ReceiptParser()
        
        # 正規表現パターン（税込優先）
        patterns = {
            'total': [
                # 最優先: 税込パターン
                r'税込合計[：:\s]*([¥￥]?[\d,]+)円?',
                r'税込[：:\s]*([¥￥]?[\d,]+)円?',
                r'\(税込\)[：:\s]*([¥￥]?[\d,]+)円?',
                r'([¥￥]?[\d,]+)円?[\s]*\(税込\)',
                r'お預り[：:\s]*([¥￥]?[\d,]+)円?',  # お預りは通常税込金額
                # 次優先: 合計パターン
                r'合[\s]*計[：:\s]*([¥￥]?[\d,]+)円?',
                r'お会計[：:\s]*([¥￥]?[\d,]+)円?',
                r'お買上計[：:\s]*([¥￥]?[\d,]+)円?',
                r'総額[：:\s]*([¥￥]?[\d,]+)円?',
                r'お支払[：:\s]*([¥￥]?[\d,]+)円?',
                r'合計金額[：:\s]*([¥￥]?[\d,]+)円?',
                r'現金[：:\s]*([¥￥]?[\d,]+)円?',  # 現金支払額
                r'計[：:\s]*([¥￥]?[\d,]+)円?'
            ],
            'subtotal': [
                # 小計・税抜パターン
                r'小計[：:\s]*([¥￥]?[\d,]+)円?',
                r'税抜[：:\s]*([¥￥]?[\d,]+)円?',
                r'税抜合計[：:\s]*([¥￥]?[\d,]+)円?',
                r'商品計[：:\s]*([¥￥]?[\d,]+)円?'
            ],
            'tax': [
                r'消費税[：:\s]*([¥￥]?[\d,]+)円?',
                r'内税[：:\s]*([¥￥]?[\d,]+)円?',
                r'外税[：:\s]*([¥￥]?[\d,]+)円?',
                r'内消費税[：:\s]*([¥￥]?[\d,]+)円?',
                r'内消費税等[：:\s]*([¥￥]?[\d,]+)円?',
                r'\(内税[：:\s]*([¥￥]?[\d,]+)円?\)',
                r'税[：:\s]*([¥￥]?[\d,]+)円?'  # 最後の手段
            ],
            'date': [
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
        }
        
        # 고급 파서로 금액 추출
        parsed_amounts = parser.parse_receipt(full_text)
        
        # データ抽出（고급 파서 결과 우선 사용）
        receipt_data = {
            'vendor': self._extract_vendor(full_text),
            'total': parsed_amounts.get('total'),
            'subtotal': parsed_amounts.get('subtotal'),
            'tax': parsed_amounts.get('tax'),
            'tax_rate': parsed_amounts.get('tax_rate', 0.1),
            'issue_date': self._extract_date(full_text, patterns['date']),
            'payment_method': self._detect_payment_method(full_text),
            'document_type': self._detect_document_type(full_text),
            'raw_text': full_text
        }
        
        # 手書き文書の検出
        if self._is_handwritten_document(full_text, ocr_result):
            logger.warning("Handwritten document detected, applying stricter validation")
            # 手書き文書の場合、より厳格な検証
            if receipt_data['total'] and receipt_data['total'] > 100000:  # 10万円超
                logger.warning(f"Handwritten doc with large amount: {receipt_data['total']}, reducing confidence")
                # 手書きで大金額は疑わしいので、金額を制限
                receipt_data['total'] = None
                receipt_data['tax'] = None
        
        # 고급 파서가 이미 tax_rate를 계산했으므로, 추가 계산은 불필요
        # 파서가 실패한 경우만 폴백
        if not receipt_data['tax_rate'] and receipt_data['total'] and receipt_data['tax']:
            tax_rate = receipt_data['tax'] / receipt_data['total']
            if 0.07 <= tax_rate <= 0.09:
                receipt_data['tax_rate'] = 0.08
            elif 0.09 < tax_rate <= 0.11:
                receipt_data['tax_rate'] = 0.10
            else:
                receipt_data['tax_rate'] = 0.10  # デフォルト値
        
        # 最終検証
        receipt_data = self._validate_receipt_data(receipt_data)
        
        return receipt_data
    
    def _extract_vendor(self, text: str) -> Optional[str]:
        """販売者/店名抽出 - 改善版（発行元と宛名を区別）"""
        lines = text.split('\n')
        
        # 宛名パターン（これらは発行元ではない）
        recipient_patterns = [
            r'様$',
            r'御中$',
            r'^\s*お客様',
            r'^\s*宛名',
            r'^\s*To:',
            r'^\s*あて名'
        ]
        
        # 発行元の手がかりとなるキーワード
        vendor_indicators = [
            '住所', '〒', 'TEL', '電話', '☎',  # 住所・電話が近くにある
            '発行', '店舗', '営業',  # 発行元情報
        ]
        
        # 除外すべきキーワード（基本的なもののみ）
        exclude_keywords = [
            '領収証', '領収書', 'レシート', '計算', '御買上', 
            '売上票', 'お買い上け', '納品書', '請求書', 'RECEIPT',
            '登録番号', 'T5010002022488', '明細', '控え',
            '但し', 'として', '内訳', '合計', '小計',
            '印紙', '収入印紙', '税込', '税抜', '内税',
            '下記の', '下記', '上記', '以下', '以上'  # 指示語も除外
        ]
        
        # 無効な店舗名パターン（日付や異常な形式）
        invalid_patterns = [
            r'\d+月\d+日',  # 「12月25日」のような日付
            r'\d{2,}月',     # 「72月」のような異常な月
            r'^\d+日$',      # 数字+「日」だけ
            r'^[\d\.]+$',    # 数字だけ
            r'^[=\-\+\*\/]+',  # 記号で始まる
            r'^\d+\s+\d+/\d+$',  # 「1122300 3/36」のようなパターン
            r'^\d{6,}',  # 6桁以上の数字で始まる
            r'^\d+/\d+$',  # 分数のみ
        ]
        
        # 優先順位リスト（高い順）
        candidates = []
        
        # 各行を解析
        for i, line in enumerate(lines[:15]):  # 最初の15行を優先的にチェック
            cleaned = line.strip()
            if not cleaned or len(cleaned) < 2:
                continue
            
            # 宛名パターンチェック（これらは除外）
            is_recipient = False
            for pattern in recipient_patterns:
                if re.search(pattern, cleaned, re.IGNORECASE):
                    is_recipient = True
                    logger.debug(f"Skipping recipient line: {cleaned}")
                    break
            
            if is_recipient:
                continue  # 宛名は発行元ではないのでスキップ
            
            # Priority 1: 住所・電話番号の近くにある店舗名（上下2行をチェック）
            priority_boost = 0
            if i > 0:
                prev_line = lines[i-1] if i > 0 else ""
                if any(indicator in prev_line for indicator in vendor_indicators):
                    priority_boost = 10
            if i < len(lines) - 1:
                next_line = lines[i+1]
                if any(indicator in next_line for indicator in vendor_indicators):
                    priority_boost = 10
            
            # Priority 2: 会社名パターン（発行元の可能性高）
            if any(keyword in cleaned for keyword in ['株式会社', '有限会社', '合同会社', '(株)', '㈱']):
                if not any(kw in cleaned for kw in exclude_keywords):
                    candidates.append((3 - priority_boost, cleaned))
            
            # Priority 3: 店舗名パターン（発行元の可能性高）
            elif any(keyword in cleaned for keyword in ['店', 'ストア', 'マート', 'スーパー', '商店', 'センター']):
                if not any(kw in cleaned for kw in exclude_keywords):
                    candidates.append((4 - priority_boost, cleaned))
            
            # Priority 4: チェーン店名パターン
            elif any(chain in cleaned for chain in ['セブンイレブン', 'ファミリーマート', 'ローソン', 'イオン', 'ダイソー']):
                candidates.append((2, cleaned))
            
            # Priority 5: 上部の大きなテキスト（ロゴ等の可能性）
            elif i < 5 and not any(kw in cleaned for kw in exclude_keywords):
                # 数字だけでない、有効な文字列
                if not cleaned.replace(' ', '').replace('-', '').replace('/', '').isdigit():
                    digit_count = sum(c.isdigit() for c in cleaned)
                    if len(cleaned) > 0 and digit_count / len(cleaned) < 0.5:
                        candidates.append((6 - priority_boost, cleaned))
        
        # 優先順位でソートして最初のものを返す
        if candidates:
            candidates.sort(key=lambda x: x[0])
            
            # 最終候補を検証
            for _, vendor_name in candidates:
                # 無効なパターンチェック
                is_invalid = False
                for pattern in invalid_patterns:
                    if re.search(pattern, vendor_name):
                        logger.warning(f"Invalid vendor name pattern detected: {vendor_name}")
                        is_invalid = True
                        break
                
                # 長さチェック（2文字以上、50文字以下）
                if len(vendor_name) < 2 or len(vendor_name) > 50:
                    logger.warning(f"Invalid vendor name length: {vendor_name}")
                    is_invalid = True
                
                # 数字のみ、またはほとんど数字の場合も除外
                clean_name = vendor_name.replace(' ', '').replace('/', '').replace('-', '')
                if clean_name.isdigit():
                    logger.warning(f"Vendor name is all digits: {vendor_name}")
                    is_invalid = True
                
                if not is_invalid:
                    return vendor_name
        
        # 何も見つからない場合は「Unknown」を返す（Noneだと保存されない）
        return "Unknown"
    
    def _extract_amount(self, text: str, patterns: list) -> Optional[float]:
        """金額抽出 - 異常値検証付き"""
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # 最初のマッチから数字のみ抽出
                amount_str = matches[0]
                amount_str = re.sub(r'[¥￥,円]', '', amount_str)
                try:
                    amount = float(amount_str)
                    
                    # 金額の妥当性チェック
                    # 一般的な領収書は100万円未満が多い
                    if amount > 1000000:  # 100万円超
                        logger.warning(f"Suspiciously large amount detected: {amount}")
                        # 10万円を超える場合は警告だけ出して続行
                        # （大きな買い物もあるため完全には除外しない）
                        if amount > 10000000:  # 1000万円超は異常値として除外
                            logger.error(f"Amount too large, skipping: {amount}")
                            continue
                    
                    if amount <= 0:
                        logger.warning(f"Invalid amount (zero or negative): {amount}")
                        continue
                    
                    return amount
                except:
                    continue
        return None
    
    def _extract_tax_inclusive_amount(self, text: str, patterns: dict) -> Optional[float]:
        """税込金額を優先的に抽出"""
        # まず税込明記パターンを優先
        tax_inclusive_patterns = patterns['total'][:5]  # 最初の5つは税込パターン
        result = self._extract_amount(text, tax_inclusive_patterns)
        if result:
            return result
        
        # 税込パターンがなければ、通常の合計パターン
        return self._extract_amount(text, patterns['total'])
    
    def _extract_date(self, text: str, patterns: list) -> Optional[str]:
        """日付抽出 - 改善版（厳格な日付検証と省略形式対応）"""
        lines = text.split('\n')
        date_candidates = []  # (priority, line_index, date_string, normalized_date)
        
        # 日付キーワード（これらの近くにある日付を優先）
        date_keywords = ['日付', '発行日', 'Date', '年月日', '取引日', '購入日', 'レシート', '日時']
        
        # 現在の年（令和の計算用）
        from datetime import datetime
        current_year = datetime.now().year
        current_reiwa = current_year - 2018  # 令和元年 = 2019
        
        for i, line in enumerate(lines[:25]):  # 最初の25行をチェック
            # 日付キーワードが含まれる行は優先度高
            has_keyword = any(kw in line for kw in date_keywords)
            priority = 20 if has_keyword else 10
            
            # 上部（最初の7行）の日付は優先度高
            if i < 7:
                priority += 5
            
            # レジ番号や時刻の近くも優先
            if any(kw in line for kw in ['レジ', '時', ':', 'No.', '#']):
                priority += 3
            
            for pattern_idx, pattern in enumerate(patterns):
                matches = re.findall(pattern, line)
                for match in matches:
                    # 日付文字列を取得
                    date_str = match if isinstance(match, str) else match[0]
                    normalized_date = None
                    
                    # パターンごとの日付正規化と優先度調整
                    if '令和' in date_str:
                        # 令和の日付はそのまま使用
                        normalized_date = date_str
                        priority += 15  # 元号付きは信頼度最高
                    elif '平成' in date_str:
                        # 平成の日付もそのまま使用
                        normalized_date = date_str
                        priority += 15
                    elif 'R' in date_str and re.match(r'R\d+', date_str):
                        # R6.12.25形式
                        normalized_date = date_str
                        priority += 12
                    elif 'H' in date_str and re.match(r'H\d+', date_str):
                        # H31.4.30形式
                        normalized_date = date_str
                        priority += 12
                    elif re.match(r'\d{4}[年/-]', date_str):
                        # 西暦を含む形式
                        year_match = re.search(r'(20\d{2})', date_str)
                        if year_match:
                            year = int(year_match.group(1))
                            # 2020-2025年の範囲のみ許可（現実的な範囲）
                            if 2020 <= year <= 2025:
                                normalized_date = date_str
                                priority += 10
                    elif re.match(r'\d{1}年\d{1,2}月\d{1,2}日', date_str):
                        # 「6年11月26日」のような省略形式を令和として解釈
                        m = re.match(r'(\d{1})年(\d{1,2})月(\d{1,2})日', date_str)
                        if m:
                            year_digit = int(m.group(1))
                            month = int(m.group(2))
                            day = int(m.group(3))
                            # 令和の年として解釈（6年 = 令和6年）
                            if 1 <= year_digit <= current_reiwa and 1 <= month <= 12 and 1 <= day <= 31:
                                # 令和形式に変換して保存
                                normalized_date = f"令和{year_digit}年{month}月{day}日"
                                priority += 8  # 省略形式は中程度の信頼度
                                logger.info(f"Converted abbreviated date: {date_str} -> {normalized_date}")
                    elif re.match(r'20\d{6}', date_str):
                        # 20241225形式（8桁の数字）
                        year = int(date_str[0:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])
                        if 2020 <= year <= 2025 and 1 <= month <= 12 and 1 <= day <= 31:
                            normalized_date = date_str
                            priority += 7
                    
                    # 有効な日付のみ候補に追加
                    if normalized_date:
                        date_candidates.append((priority, i, date_str, normalized_date))
                        logger.debug(f"Valid date found: {normalized_date} (original: {date_str}, priority={priority}, line={i})")
        
        # 最も優先度の高い日付を選択
        if date_candidates:
            # 優先度（高い方が良い）、行番号（小さい方が良い）でソート
            date_candidates.sort(key=lambda x: (-x[0], x[1]))
            selected = date_candidates[0]
            logger.info(f"Selected date: {selected[3]} (original: {selected[2]}) from {len(date_candidates)} candidates")
            # 元の形式を返す（正規化された形式ではなく、OCRで読み取った原文）
            return selected[2]
        
        logger.warning("No valid date found in the text")
        return None
    
    def _detect_payment_method(self, text: str) -> str:
        """決済方法検出"""
        payment_keywords = {
            'クレジット': 'クレジット',
            'カード': 'クレジット',
            'VISA': 'クレジット',
            'Master': 'クレジット',
            'JCB': 'クレジット',
            '現金': '現金',
            'Suica': '電子マネー',
            'PASMO': '電子マネー',
            'PayPay': '電子マネー',
            'LINE Pay': '電子マネー',
            '楽天ペイ': '電子マネー'
        }
        
        for keyword, method in payment_keywords.items():
            if keyword.lower() in text.lower():
                return method
        
        # デフォルト値
        return '現金' if '現金' in text else '不明'
    
    def _detect_document_type(self, text: str) -> str:
        """文書タイプ検出"""
        doc_types = {
            '領収書': '領収書',
            '領収証': '領収書',
            'レシート': 'レシート',
            '請求書': '請求書',
            'インボイス': '請求書',
            '見積書': '見積書',
            '納品書': '納品書'
        }
        
        for keyword, doc_type in doc_types.items():
            if keyword in text:
                return doc_type
        
        return 'レシート'  # デフォルト値
    
    def _is_handwritten_document(self, text: str, ocr_result: Dict[str, Any]) -> bool:
        """手書き文書の検出"""
        # 手書き文書の特徴
        handwritten_indicators = [
            '計算領収証',  # 手書き計算書でよく使われる
            '計算（領収証）',
            '様',  # 手書きでよく使われる敬称（ただし一般的すぎるので他の条件と組み合わせ）
        ]
        
        # OCR confidence scoreが低い場合
        blocks = ocr_result.get('blocks', [])
        if blocks:
            avg_confidence = sum(b.get('confidence', 0) for b in blocks) / len(blocks)
            if avg_confidence < 0.8:  # 80%未満は手書きの可能性
                return True
        
        # 手書き指標が複数ある場合
        indicator_count = sum(1 for indicator in handwritten_indicators if indicator in text)
        if indicator_count >= 2:
            return True
        
        # テキストが乱れている（改行が多い、短い行が多い）
        lines = text.split('\n')
        short_lines = sum(1 for line in lines if 0 < len(line.strip()) < 3)
        if len(lines) > 0 and short_lines / len(lines) > 0.5:  # 50%以上が短い行
            return True
        
        return False
    
    def _validate_receipt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """レシートデータの最終検証と修正"""
        # 税額が総額を超える場合は無効
        if data.get('tax') and data.get('total'):
            if data['tax'] > data['total']:
                logger.error(f"Tax amount {data['tax']} exceeds total {data['total']}, clearing tax")
                data['tax'] = None
                data['tax_rate'] = None
        
        # 小計が総額を超える場合は無効
        if data.get('subtotal') and data.get('total'):
            if data['subtotal'] > data['total']:
                logger.error(f"Subtotal {data['subtotal']} exceeds total {data['total']}, clearing subtotal")
                data['subtotal'] = None
        
        # 店舗名が「Unknown」で金額が大きい場合は疑わしい
        if data.get('vendor') == 'Unknown' and data.get('total'):
            if data['total'] > 50000:  # 5万円超
                logger.warning(f"Unknown vendor with large amount {data['total']}, flagging as suspicious")
                # メモに警告を追加
                data['memo'] = (data.get('memo', '') + ' [自動検証:店舗名不明の高額取引]').strip()
        
        # 総額が0円または異常に小さい場合
        if not data.get('total') or data.get('total', 0) < 1:
            logger.error(f"Invalid total amount: {data.get('total')}, receipt data may be corrupt")
            # 0円のレシートは保存しない
            data['total'] = None
        
        return data

    async def extract_receipt_data(self, image_path: str, ocr_text: str = None) -> Dict[str, Any]:
        """
        レシート画像からデータ抽出（Gemini互換インターフェース）
        """
        try:
            # Check if client is initialized
            if not self.client:
                logger.error("Vision API client not initialized, falling back to error response")
                raise Exception("Vision API client not initialized")
            
            # OCR実行
            ocr_result = self.extract_text_from_image(image_path)
            
            # レシートデータパース
            receipt_data = self.parse_receipt_data(ocr_result)
            
            # 日本の元号日付変換（既存ユーティリティ使用）
            if receipt_data.get('issue_date'):
                from utils.japanese_date import parse_japanese_date
                parsed_date = parse_japanese_date(receipt_data['issue_date'])
                if parsed_date:
                    receipt_data['issue_date'] = parsed_date
                else:
                    # パース失敗時は文字列をそのまま使用（今日の日付は使わない）
                    try:
                        receipt_data['issue_date'] = datetime.strptime(
                            receipt_data['issue_date'], '%Y-%m-%d'
                        )
                    except:
                        # 日付が解析できない場合は文字列のまま保持
                        # datetime.now()は使わない（今日の日付になってしまうため）
                        logger.warning(f"Could not parse date: {receipt_data.get('issue_date')}, keeping as string")
                        pass  # issue_dateは文字列のまま
            
            # Simple normalization for document type
            doc_type = receipt_data.get('document_type', 'レシート')
            # Handle composite types by taking first part
            if doc_type and '・' in doc_type:
                doc_type = doc_type.split('・')[0]
            
            payment = receipt_data.get('payment_method', '現金')
            
            # 最終検証: vendorが数字のみの場合はUnknownに変更
            final_vendor = receipt_data.get('vendor', 'Unknown')
            if final_vendor and final_vendor.replace(' ', '').replace('/', '').replace('-', '').isdigit():
                logger.warning(f"Vendor name is numeric, changing to Unknown: {final_vendor}")
                final_vendor = 'Unknown'
            
            # 金額が0円の場合はエラーを返す
            if not receipt_data.get('total') or receipt_data.get('total', 0) < 1:
                logger.error("Total amount is zero or invalid, returning error")
                raise Exception("Invalid receipt - zero amount")
            
            # Geminiレスポンス形式と互換できるように変換
            return {
                "vendor": final_vendor,
                "document_type": doc_type,
                "issue_date": receipt_data.get('issue_date', None),  # 日付が無い場合はNone（今日の日付は使わない）
                "currency": "JPY",
                "total": receipt_data.get('total', 0),
                "subtotal": receipt_data.get('subtotal', 0),
                "tax": receipt_data.get('tax', 0),
                "tax_rate": receipt_data.get('tax_rate', 0.10),
                "line_items": [],  # Vision APIでは詳細品目抽出が難しい
                "payment_method": payment,
                "memo": f"OCR by Vision API",
                "raw_ocr_text": receipt_data.get('raw_text', '')
            }
            
        except Exception as e:
            logger.error(f"Receipt data extraction failed: {e}")
            # エラー時はデフォルト値を返す
            return {
                "vendor": "OCR Failed",
                "document_type": "レシート",
                "issue_date": None,  # エラー時も今日の日付は使わない
                "currency": "JPY",
                "total": 0,
                "subtotal": 0,
                "tax": 0,
                "tax_rate": 0.10,
                "line_items": [],
                "payment_method": "不明",
                "memo": f"OCR Error: {str(e)}",
                "raw_ocr_text": ""
            }