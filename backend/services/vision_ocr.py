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
        """
        try:
            # JSONキーなしでデフォルト認証使用
            self.client = vision.ImageAnnotatorClient()
            logger.info("Vision API client initialized with default credentials")
        except Exception as e:
            logger.error(f"Failed to initialize Vision API client: {e}")
            logger.info("Please run: gcloud auth application-default login")
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
            response = self.client.document_text_detection(
                image=image,
                image_context={'language_hints': ['ja', 'en']}
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
        
        # 正規表現パターン
        patterns = {
            'total': [
                r'合計[：:\s]*([¥￥]?[\d,]+)円?',
                r'総額[：:\s]*([¥￥]?[\d,]+)円?',
                r'お支払[：:\s]*([¥￥]?[\d,]+)円?',
                r'合計金額[：:\s]*([¥￥]?[\d,]+)円?',
                r'計[：:\s]*([¥￥]?[\d,]+)円?'
            ],
            'tax': [
                r'消費税[：:\s]*([¥￥]?[\d,]+)円?',
                r'内税[：:\s]*([¥￥]?[\d,]+)円?',
                r'税[：:\s]*([¥￥]?[\d,]+)円?',
                r'\(税込[：:\s]*([¥￥]?[\d,]+)円?\)',
                r'内消費税等[：:\s]*([¥￥]?[\d,]+)円?'
            ],
            'date': [
                r'(令和\d+年\d{1,2}月\d{1,2}日)',  # 令和6年12月25日
                r'(令和元年\d{1,2}月\d{1,2}日)',    # 令和元年
                r'(平成\d+年\d{1,2}月\d{1,2}日)',  # 平成31年4月30日
                r'(R\d+[\.\/\-]\d{1,2}[\.\/\-]\d{1,2})',  # R6.12.25, R6/12/25
                r'(H\d+[\.\/\-]\d{1,2}[\.\/\-]\d{1,2})',  # H31.4.30
                r'(\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2}[日]?)',  # 2024年12月25日, 2024/12/25
                r'(\d{4}-\d{2}-\d{2})',            # 2024-12-25
                r'(\d{2}/\d{2}/\d{2})',            # 24/12/25
                r'(\d{8})',                        # 20241225
            ]
        }
        
        # データ抽出
        receipt_data = {
            'vendor': self._extract_vendor(full_text),
            'total': self._extract_amount(full_text, patterns['total']),
            'tax': self._extract_amount(full_text, patterns['tax']),
            'issue_date': self._extract_date(full_text, patterns['date']),
            'payment_method': self._detect_payment_method(full_text),
            'document_type': self._detect_document_type(full_text),
            'raw_text': full_text
        }
        
        # 税率計算
        if receipt_data['total'] and receipt_data['tax']:
            tax_rate = receipt_data['tax'] / receipt_data['total']
            if 0.07 <= tax_rate <= 0.09:
                receipt_data['tax_rate'] = 0.08
            elif 0.09 < tax_rate <= 0.11:
                receipt_data['tax_rate'] = 0.10
            else:
                receipt_data['tax_rate'] = 0.10  # デフォルト値
        else:
            receipt_data['tax_rate'] = None
        
        # subtotal計算
        if receipt_data['total'] and receipt_data['tax']:
            receipt_data['subtotal'] = receipt_data['total'] - receipt_data['tax']
        else:
            receipt_data['subtotal'] = receipt_data['total']
        
        return receipt_data
    
    def _extract_vendor(self, text: str) -> Optional[str]:
        """販売者/店名抽出"""
        lines = text.split('\n')
        
        # 一般的にレシート上部にある店名を探す
        for i, line in enumerate(lines[:5]):  # 上部5行確認
            # 会社名パターン
            if any(keyword in line for keyword in ['株式会社', '有限会社', '合同会社', '(株)', '㈱']):
                return line.strip()
            # 店舗名パターン
            if any(keyword in line for keyword in ['店', 'ストア', 'マート', 'スーパー']):
                return line.strip()
        
        # 最初の空でない行をvendorとして推定
        for line in lines:
            cleaned = line.strip()
            if cleaned and len(cleaned) > 2:
                return cleaned
        
        return None
    
    def _extract_amount(self, text: str, patterns: list) -> Optional[float]:
        """金額抽出"""
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # 最初のマッチから数字のみ抽出
                amount_str = matches[0]
                amount_str = re.sub(r'[¥￥,円]', '', amount_str)
                try:
                    return float(amount_str)
                except:
                    continue
        return None
    
    def _extract_date(self, text: str, patterns: list) -> Optional[str]:
        """日付抽出（日本の元号含む）"""
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                date_str = matches[0]
                # 日本の元号はそのまま返す（別途処理必要）
                return date_str
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
                    # パース失敗時は文字列をそのまま使用
                    try:
                        receipt_data['issue_date'] = datetime.strptime(
                            receipt_data['issue_date'], '%Y-%m-%d'
                        )
                    except:
                        receipt_data['issue_date'] = datetime.now()
            
            # Simple normalization for document type
            doc_type = receipt_data.get('document_type', 'レシート')
            # Handle composite types by taking first part
            if doc_type and '・' in doc_type:
                doc_type = doc_type.split('・')[0]
            
            payment = receipt_data.get('payment_method', '現金')
            
            # Geminiレスポンス形式と互換できるように変換
            return {
                "vendor": receipt_data.get('vendor', 'Unknown'),
                "document_type": doc_type,
                "issue_date": receipt_data.get('issue_date', datetime.now()),
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
                "issue_date": datetime.now(),
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