"""
シンプルな統合ビジョンサービス (GPT-4V または Gemini Vision 直接使用)
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from PIL import Image
import base64
import io

logger = logging.getLogger(__name__)

class SimpleVisionService:
    def __init__(self):
        """統合ビジョンサービス初期化"""
        self.provider = os.getenv("VISION_PROVIDER", "gemini").lower()
        
        if self.provider == "openai":
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.model = "gpt-4o"
                logger.info("OpenAI GPT-4 Vision initialized")
            else:
                raise ValueError("OPENAI_API_KEY not set")
                
        elif self.provider == "gemini":
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini Vision initialized")
            else:
                raise ValueError("GEMINI_API_KEY not set")
    
    def extract_receipt(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        画像から直接レシートデータを抽出（1ステップ処理）
        """
        prompt = """この領収書画像から以下の情報を抽出してください。
        
        必須フィールド:
        - vendor: 店舗名
        - date: 日付 (YYYY-MM-DD形式)
        - total: 合計金額 (数値のみ)
        - items: 商品リスト [{name: 商品名, price: 価格}]
        
        オプションフィールド:
        - time: 時刻 (HH:MM形式)
        - tax: 消費税額
        - payment_method: 支払方法
        
        JSON形式で返答してください。"""
        
        try:
            if self.provider == "openai":
                return self._extract_with_openai(image_path, prompt)
            else:
                return self._extract_with_gemini(image_path, prompt)
                
        except Exception as e:
            logger.error(f"Vision extraction failed: {e}")
            return None
    
    def _extract_with_openai(self, image_path: str, prompt: str) -> Dict:
        """OpenAI GPT-4 Vision"""
        with Image.open(image_path) as img:
            # リサイズで料金削減
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}",
                        "detail": "low"  # 料金削減
                    }}
                ]
            }],
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _extract_with_gemini(self, image_path: str, prompt: str) -> Dict:
        """Gemini Vision"""
        image = Image.open(image_path)
        response = self.model.generate_content([image, prompt])
        
        # JSONパース
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        
        return json.loads(text)

# 使用例
if __name__ == "__main__":
    service = SimpleVisionService()
    result = service.extract_receipt("sample_receipt.jpg")
    print(json.dumps(result, indent=2, ensure_ascii=False))