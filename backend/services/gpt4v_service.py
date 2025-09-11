"""
GPT-4V統合ビジョンサービス
全てのOCR/Vision処理をGPT-4Vに統一
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from PIL import Image
import base64
import io
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

class GPT4VisionService:
    def __init__(self):
        """GPT-4 Vision APIクライアント初期化"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here":
            # デフォルトキーを設定（後で環境変数で上書き）
            logger.warning("OPENAI_API_KEY not set - please set it in .env file")
            raise ValueError("OPENAI_API_KEY is required for GPT-4V service")
        
        try:
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4o"  # 最新のGPT-4 Visionモデル
            logger.info(f"✅ GPT-4 Vision service initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize GPT-4V: {e}")
            raise
    
    def extract_receipt(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        画像から直接レシートデータを抽出（1ステップ処理）
        Cloud Vision APIやGeminiを使わず、GPT-4Vのみで処理
        """
        try:
            # 画像準備
            image_data = self._prepare_image(image_path)
            
            # プロンプト（日本の領収書に最適化）
            prompt = self._get_receipt_prompt()
            
            # GPT-4V API呼び出し
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}",
                            "detail": "high"  # 高精度モード（レシート向け）
                        }}
                    ]
                }],
                max_tokens=1000,
                temperature=0.1,  # 低温度で一貫性向上
                response_format={"type": "json_object"}
            )
            
            # レスポンス解析
            result = json.loads(response.choices[0].message.content)
            
            # データ検証と正規化
            result = self._validate_and_normalize(result)
            
            logger.info(f"✅ Receipt extracted successfully: {result.get('vendor', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"GPT-4V extraction failed: {e}")
            return None
    
    def _prepare_image(self, image_path: str) -> str:
        """画像を最適化してBase64エンコード"""
        with Image.open(image_path) as img:
            # EXIF回転を適用
            img = self._fix_image_rotation(img)
            
            # 最適サイズにリサイズ（コスト削減 & 品質維持）
            # GPT-4Vは2048x2048まで対応だが、領収書なら1024で十分
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # コントラスト強調（領収書の文字を見やすく）
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            
            # JPEG変換（品質90でバランス良く）
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=90)
            return base64.b64encode(buffered.getvalue()).decode()
    
    def _fix_image_rotation(self, img: Image) -> Image:
        """EXIF情報に基づいて画像を正しい向きに回転"""
        try:
            from PIL import ExifTags
            
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            
            exif = img._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation)
                if orientation_value:
                    rotations = {
                        3: 180,
                        6: 270,
                        8: 90
                    }
                    if orientation_value in rotations:
                        img = img.rotate(rotations[orientation_value], expand=True)
        except:
            pass
        
        return img
    
    def _get_receipt_prompt(self) -> str:
        """最適化された領収書抽出プロンプト"""
        return """あなたは領収書解析の専門家です。
この領収書画像から以下の情報を正確に抽出してください。

必須情報:
- vendor: 店舗名（会社名や店名）
- date: 日付（YYYY-MM-DD形式に変換）
- total: 合計金額（数値のみ、¥や円を除く）
- items: 商品リスト（配列）
  - name: 商品名
  - price: 単価（数値のみ）
  - quantity: 数量（デフォルト1）

オプション情報（存在する場合）:
- store_number: 店舗番号
- receipt_number: レシート番号
- time: 時刻（HH:MM形式）
- subtotal: 小計
- tax: 消費税額
- tax_rate: 税率（%）
- payment_method: 支払方法（現金/カード/電子マネー等）
- cashier: レジ担当者
- points: ポイント情報
- phone: 電話番号
- address: 住所

重要な注意事項:
1. 日本語の領収書の場合、日付は和暦の可能性があるので西暦に変換
2. 金額は必ず数値のみ（カンマや円記号を除去）
3. 不明な項目はnullとする（推測しない）
4. 手書きの領収書にも対応する
5. 複数の商品がある場合は全て抽出

必ずJSON形式で返答してください。
"""
    
    def _validate_and_normalize(self, data: Dict) -> Dict:
        """抽出データの検証と正規化"""
        # 必須フィールドの確認
        required = ['vendor', 'date', 'total']
        for field in required:
            if field not in data or not data[field]:
                logger.warning(f"Missing required field: {field}")
                data[field] = "不明" if field == 'vendor' else None
        
        # 日付の正規化
        if data.get('date'):
            data['date'] = self._normalize_date(data['date'])
        
        # 金額の正規化
        for field in ['total', 'subtotal', 'tax']:
            if field in data and data[field]:
                data[field] = self._normalize_amount(data[field])
        
        # 商品リストの正規化
        if 'items' in data and isinstance(data['items'], list):
            for item in data['items']:
                if 'price' in item:
                    item['price'] = self._normalize_amount(item['price'])
                if 'quantity' not in item:
                    item['quantity'] = 1
        else:
            data['items'] = []
        
        # 処理メタデータ追加
        data['processed_at'] = datetime.now().isoformat()
        data['processor'] = 'GPT-4V'
        data['confidence'] = 0.95  # GPT-4Vの高い信頼度
        
        return data
    
    def _normalize_date(self, date_str: str) -> str:
        """日付を YYYY-MM-DD 形式に正規化"""
        if not date_str:
            return None
        
        # すでに正しい形式の場合
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            return date_str
        
        # 様々な形式を試す
        from datetime import datetime
        formats = [
            '%Y年%m月%d日', '%Y/%m/%d', '%Y-%m-%d',
            '%Y.%m.%d', '%Y%m%d', '%m/%d/%Y'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.replace(' ', ''), fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
        
        # 和暦変換（令和）
        if '令和' in date_str:
            # 簡易変換（令和元年=2019）
            import re
            match = re.search(r'令和(\d+)年', date_str)
            if match:
                reiwa_year = int(match.group(1))
                year = 2018 + reiwa_year
                date_str = date_str.replace(f'令和{reiwa_year}年', f'{year}年')
                return self._normalize_date(date_str)
        
        return date_str  # 変換できない場合は元の文字列
    
    def _normalize_amount(self, amount) -> float:
        """金額を数値に正規化"""
        if isinstance(amount, (int, float)):
            return float(amount)
        
        if isinstance(amount, str):
            # 不要な文字を除去
            amount = amount.replace('¥', '').replace('￥', '')
            amount = amount.replace(',', '').replace('、', '')
            amount = amount.replace('円', '').replace(' ', '')
            
            try:
                return float(amount)
            except:
                logger.warning(f"Could not parse amount: {amount}")
                return 0.0
        
        return 0.0
    
    def batch_process(self, image_paths: List[str]) -> List[Dict]:
        """複数画像のバッチ処理（効率化）"""
        results = []
        for path in image_paths:
            result = self.extract_receipt(path)
            if result:
                results.append(result)
        return results
    
    def get_usage_stats(self) -> Dict:
        """API使用統計（コスト管理用）"""
        # TODO: 実装（使用回数、コスト計算など）
        return {
            'provider': 'OpenAI',
            'model': self.model,
            'status': 'active'
        }

# シンプルなラッパー関数
def extract_receipt_simple(image_path: str) -> Dict:
    """簡単に使えるラッパー関数"""
    service = GPT4VisionService()
    return service.extract_receipt(image_path)