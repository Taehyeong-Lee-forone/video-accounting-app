"""
OpenAI GPT-4 APIを使用したOCR後処理サービス
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from PIL import Image
import base64
import io
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        """OpenAI APIクライアント初期化"""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "your-openai-api-key-here":
            try:
                self.client = OpenAI(api_key=api_key)
                self.model = "gpt-4o"  # GPT-4 Vision対応モデル
                logger.info("OpenAI API client initialized successfully")
            except Exception as e:
                logger.warning(f"OpenAI model could not be initialized: {e}")
                self.client = None
        else:
            logger.warning("OPENAI_API_KEY not set")
            self.client = None
    
    def process_receipt_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        画像から領収書情報を抽出（GPT-4 Vision使用）
        """
        if not self.client:
            logger.warning("OpenAI client not initialized")
            return None
        
        try:
            # 画像をBase64エンコード
            with Image.open(image_path) as img:
                # 画像サイズを適切に調整
                max_size = (1024, 1024)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Base64エンコード
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # GPT-4 Visionへのリクエスト
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """あなたは日本の領収書/レシートの専門的な読取りアシスタントです。
画像から情報を正確に抽出して、JSONフォーマットで返してください。"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self._get_prompt()
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                response_format={ "type": "json_object" },  # JSON形式を強制
                temperature=0.1,  # 安定した出力のため低温度
                max_tokens=1000
            )
            
            # レスポンスをパース
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Successfully processed receipt with OpenAI: {result.get('vendor', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    def process_ocr_text(self, ocr_text: str, image_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        OCRテキストから構造化データを抽出
        画像がある場合はGPT-4 Visionを使用、なければテキストのみ処理
        """
        if not self.client:
            logger.warning("OpenAI client not initialized")
            return None
        
        # 画像がある場合はVision APIを使用
        if image_path and os.path.exists(image_path):
            return self.process_receipt_image(image_path)
        
        # テキストのみの処理
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",  # テキスト処理用モデル
                messages=[
                    {
                        "role": "system",
                        "content": """あなたは日本の領収書/レシートのテキスト解析専門家です。
OCRで読み取られたテキストから、正確に情報を抽出してJSONフォーマットで返してください。"""
                    },
                    {
                        "role": "user",
                        "content": f"{self._get_prompt()}\n\nOCRテキスト:\n{ocr_text}"
                    }
                ],
                response_format={ "type": "json_object" },
                temperature=0.1,
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Successfully processed OCR text with OpenAI")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    def _get_prompt(self) -> str:
        """プロンプトを取得（改善版）"""
        return """
【重要な識別ルール】
1. vendor（店舗名）: 領収書を「発行した」店舗・企業名
   - 領収書の上部にあるロゴや大きな文字の店舗名を優先
   - 「様」「御中」の前にある名前は宛名（購入者）なので除外
   - 住所・電話番号の近くにある店舗名を探す
   - 例: セブンイレブン、イオン、ローソン等

2. issue_date（発行日）: この領収書が発行された日付
   - 「6年11月26日」のような省略形式は「令和6年11月26日」として解釈
   - 年月日、発行日、Date、日付と書かれた近くの日付を優先
   - レジ番号や時刻の近くにある日付を優先
   - 複数の日付がある場合は、レシート上部の日付を優先
   - 今日の日付ではなく、領収書に記載された日付を抽出

3. recipient（宛名）: 領収書を「受け取る」人・企業名
   - 「様」「御中」の前にある名前
   - 手書きの場合が多い
   - 無記名の場合は null

以下のJSON形式で返してください:
{
  "vendor": "発行元の店舗・企業名",
  "recipient": "宛名（様・御中の前の名前）またはnull",
  "document_type": "領収書|請求書|レシート|見積書|その他",
  "issue_date": "領収書内の発行日（例: 令和6年11月26日、2024年11月26日）",
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
- 日付は必ずこの画像/テキスト内に表示されているものだけを使用
- 今日の日付を使わないこと
- 金額は数値として返す
- 存在しない項目はnull
"""