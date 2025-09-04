"""
AI APIサービス統合（Gemini/OpenAI切り替え対応）
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from PIL import Image

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        """AI APIの初期化（環境変数で選択）"""
        self.provider = os.getenv("AI_PROVIDER", "gemini").lower()
        self.service = None
        
        logger.info(f"Initializing AI Service with provider: {self.provider}")
        
        if self.provider == "openai":
            try:
                from services.openai_service import OpenAIService
                self.service = OpenAIService()
                logger.info("OpenAI GPT-4 service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI service: {e}")
                # フォールバックとしてGeminiを試す
                self.provider = "gemini"
        
        if self.provider == "gemini":
            try:
                import google.generativeai as genai
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                if gemini_api_key and gemini_api_key != "your-gemini-api-key-here":
                    genai.configure(api_key=gemini_api_key)
                    self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                    logger.info("Gemini service initialized")
                else:
                    logger.error("GEMINI_API_KEY not set")
                    self.gemini_model = None
            except Exception as e:
                logger.error(f"Failed to initialize Gemini service: {e}")
                self.gemini_model = None
    
    def process_receipt(self, ocr_text: str, image_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        OCRテキストまたは画像から領収書情報を抽出
        """
        if self.provider == "openai" and self.service:
            # OpenAI GPT-4を使用
            return self.service.process_ocr_text(ocr_text, image_path)
        
        elif self.provider == "gemini" and self.gemini_model:
            # Gemini APIを使用
            return self._process_with_gemini(ocr_text, image_path)
        
        else:
            logger.warning("No AI service available, using fallback extraction")
            # フォールバック: 基本的なパターンマッチング
            return self._fallback_extraction(ocr_text)
    
    def _process_with_gemini(self, ocr_text: str, image_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Gemini APIを使用した処理"""
        try:
            prompt = self._get_improved_prompt()
            
            # 画像がある場合はVision APIを使用
            if image_path and os.path.exists(image_path):
                image = Image.open(image_path)
                response = self.gemini_model.generate_content([image, prompt])
            else:
                # テキストのみの処理
                full_prompt = f"{prompt}\n\nOCRテキスト:\n{ocr_text}"
                response = self.gemini_model.generate_content(full_prompt)
            
            # JSON解析
            json_str = response.text.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            
            result = json.loads(json_str)
            logger.info(f"Successfully processed with Gemini: {result.get('vendor', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_extraction(ocr_text)
    
    def _get_improved_prompt(self) -> str:
        """改善版プロンプト（両API共通）"""
        return """あなたは日本の領収書/レシートの専門的な読取りアシスタントです。
画像から情報を正確に抽出して、以下のJSONを返してください。

【重要な識別ルール】
1. vendor（店舗名）: 領収書を「発行した」店舗・企業名
   - 領収書の上部にあるロゴや大きな文字の店舗名を優先
   - 「様」「御中」の前にある名前は宛名（購入者）なので除外
   - 住所・電話番号の近くにある店舗名を探す

2. issue_date（発行日）: この領収書が発行された日付のみ
   - 「6年11月26日」のような省略形式は「令和6年11月26日」として解釈
   - 「年月日」「発行日」「日付」「Date」と書かれた近くの日付
   - 今日の日付ではなく、領収書に記載された日付を使用

3. recipient（宛名）: 領収書を「受け取る」人・企業名
   - 「様」「御中」の前にある名前
   - 無記名の場合は null

【抽出フォーマット】
{
  "vendor": "発行元の店舗・企業名",
  "recipient": "宛名（様・御中の前の名前）またはnull",
  "document_type": "領収書|請求書|レシート|見積書|その他",
  "issue_date": "この画像内の発行日のみ（例: 令和6年11月26日）",
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
    
    def _fallback_extraction(self, ocr_text: str) -> Dict[str, Any]:
        """フォールバック: 基本的なパターンマッチング"""
        import re
        from datetime import datetime
        
        result = {
            'vendor': None,
            'total': None,
            'issue_date': None,
            'document_type': 'レシート',
            'currency': 'JPY'
        }
        
        lines = ocr_text.split('\n')
        
        # 店舗名を検出（最初の有効な行）
        for line in lines[:10]:
            line = line.strip()
            if line and len(line) > 2 and not re.match(r'^[\d\s\-\/\.:]+$', line):
                # 宛名行は除外
                if not re.search(r'様$|御中$', line):
                    result['vendor'] = line[:50]
                    break
        
        # 合計金額を検出
        total_pattern = r'合計[:\s]*[¥￥]?[\s]*([\d,]+)'
        match = re.search(total_pattern, ocr_text, re.IGNORECASE)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                result['total'] = float(amount_str)
            except:
                pass
        
        # 日付を検出（省略形式対応）
        date_patterns = [
            (r'令和(\d+)年(\d{1,2})月(\d{1,2})日', 'reiwa'),
            (r'(\d{4})年(\d{1,2})月(\d{1,2})日', 'full'),
            (r'(\d{1})年(\d{1,2})月(\d{1,2})日', 'short'),  # 省略形式
        ]
        
        for pattern, date_type in date_patterns:
            match = re.search(pattern, ocr_text)
            if match:
                if date_type == 'short':
                    # 省略形式を令和として解釈
                    year = int(match.group(1))
                    if 1 <= year <= 10:  # 令和1-10年
                        result['issue_date'] = f"令和{year}年{match.group(2)}月{match.group(3)}日"
                else:
                    result['issue_date'] = match.group(0)
                break
        
        return result
    
    def get_provider_info(self) -> Dict[str, Any]:
        """現在のプロバイダー情報を取得"""
        return {
            'provider': self.provider,
            'available': bool(self.service or self.gemini_model),
            'model': 'gpt-4o' if self.provider == 'openai' else 'gemini-1.5-flash'
        }