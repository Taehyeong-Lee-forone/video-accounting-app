"""
強化版OCRサービス - 精度向上のための複合アプローチ
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import google.generativeai as genai
from pathlib import Path

logger = logging.getLogger(__name__)

class EnhancedOCRService:
    def __init__(self):
        """強化版OCRサービスの初期化"""
        # Gemini API初期化
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key and gemini_api_key != "your-gemini-api-key-here":
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Enhanced OCR: Gemini model initialized")
        else:
            self.gemini_model = None
            logger.warning("Enhanced OCR: Gemini API key not found")
    
    def process_receipt(self, image_path: str, use_preprocessing: bool = True) -> Optional[Dict[str, Any]]:
        """
        領収書画像を処理して情報を抽出
        
        Args:
            image_path: 画像ファイルパス
            use_preprocessing: 画像前処理を行うか
        
        Returns:
            抽出された領収書情報
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None
        
        try:
            # 1. 画像前処理（オプション）
            if use_preprocessing:
                processed_image_path = self._preprocess_image(image_path)
            else:
                processed_image_path = image_path
            
            # 2. Gemini Vision APIで直接処理
            if self.gemini_model:
                result = self._process_with_gemini_vision(processed_image_path)
                if result:
                    logger.info(f"Successfully processed with Gemini Vision: {result.get('vendor', 'Unknown')}")
                    return result
            
            # 3. フォールバック: 基本的なOCR
            logger.warning("Falling back to basic OCR")
            return self._basic_ocr_extraction(processed_image_path)
            
        except Exception as e:
            logger.error(f"Enhanced OCR processing failed: {e}")
            return None
    
    def _preprocess_image(self, image_path: str) -> str:
        """
        画像前処理による品質改善
        """
        try:
            # OpenCVで画像を読み込み
            img = cv2.imread(image_path)
            
            # 1. グレースケール変換
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 2. ノイズ除去
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # 3. コントラスト調整（CLAHE）
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # 4. 二値化（Otsu's method）
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 5. 歪み補正（簡易版）
            # エッジ検出
            edges = cv2.Canny(binary, 50, 150, apertureSize=3)
            
            # 直線検出（Hough変換）
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
            
            if lines is not None and len(lines) > 0:
                # 傾き角度を計算
                angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                    if -45 < angle < 45:  # 水平に近い線のみ
                        angles.append(angle)
                
                if angles:
                    # 中央値で回転角度を決定
                    median_angle = np.median(angles)
                    if abs(median_angle) > 0.5:  # 0.5度以上の傾きがある場合
                        # 画像を回転
                        (h, w) = binary.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                        binary = cv2.warpAffine(binary, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            # 6. 処理済み画像を保存
            processed_path = image_path.replace('.jpg', '_enhanced.jpg').replace('.png', '_enhanced.png')
            cv2.imwrite(processed_path, binary)
            
            # 7. PILで追加処理
            pil_img = Image.open(processed_path)
            
            # シャープネス向上
            enhancer = ImageEnhance.Sharpness(pil_img)
            pil_img = enhancer.enhance(1.5)
            
            # 最終保存
            pil_img.save(processed_path, quality=95)
            logger.info(f"Image preprocessing completed: {processed_path}")
            
            return processed_path
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}, using original image")
            return image_path
    
    def _process_with_gemini_vision(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Gemini Vision APIで直接画像を処理
        """
        if not self.gemini_model:
            return None
        
        try:
            # 画像を開く
            image = Image.open(image_path)
            
            # 最適化されたプロンプト
            prompt = """
あなたは日本の領収書/レシート専門の高精度OCRシステムです。
画像を詳細に分析し、以下の情報を正確に抽出してください。

【抽出ルール】
1. vendor（店舗名）: 
   - 領収書上部の大きな文字/ロゴを最優先
   - 住所や電話番号の上にある名前を探す
   - 「様」「御中」がつくものは宛名なので除外
   - チェーン店名（セブンイレブン、ローソン等）を正確に認識

2. issue_date（発行日）:
   - 画像内に表示されている日付のみを抽出
   - 「6年11月26日」→「令和6年11月26日」に変換
   - レジ番号や時刻の近くの日付を優先
   - 複数の日付がある場合は最も妥当なものを選択
   - 今日の日付は絶対に使用しない

3. 金額情報:
   - 合計/総額を正確に読み取る
   - カンマ区切りの数字も正しく認識（例: 5,616円）
   - 小計と税額も可能な限り抽出

4. 文字認識のコツ:
   - 手書き文字も推測して読み取る
   - かすれた文字も文脈から推定
   - 数字の0とOの区別に注意
   - 漢字とカタカナの混在に対応

【JSON形式】
{
  "vendor": "店舗名（発行元）",
  "recipient": "宛名（様がつく名前）またはnull",
  "document_type": "領収書|請求書|レシート|見積書|その他",
  "issue_date": "発行日（例: 令和6年11月26日）",
  "currency": "JPY",
  "total": 合計金額（数値）,
  "subtotal": 小計（数値）,
  "tax": 消費税（数値）,
  "tax_rate": 0.10|0.08|null,
  "line_items": [
    {"name": "商品名", "qty": 数量, "unit_price": 単価, "amount": 金額}
  ],
  "payment_method": "現金|クレジット|電子マネー|不明",
  "address": "店舗住所",
  "phone": "電話番号",
  "confidence_score": 0.0-1.0（認識の確信度）,
  "memo": "その他の重要情報"
}

画像が不鮮明でも、可能な限り情報を抽出してください。
返答はJSON形式のみ。
"""
            
            # Gemini APIを呼び出し
            response = self.gemini_model.generate_content([image, prompt])
            
            # レスポンスをパース
            json_str = response.text.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            
            result = json.loads(json_str)
            
            # 信頼度スコアを追加
            if 'confidence_score' not in result:
                # デフォルトで高い信頼度を設定（Geminiは精度が高い）
                result['confidence_score'] = 0.85
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini Vision processing failed: {e}")
            return None
    
    def _basic_ocr_extraction(self, image_path: str) -> Dict[str, Any]:
        """
        基本的なOCR抽出（フォールバック）
        """
        return {
            "vendor": "OCR Failed",
            "document_type": "レシート",
            "issue_date": None,
            "total": 0,
            "confidence_score": 0.1,
            "memo": "Enhanced OCR failed, manual input required"
        }
    
    def process_multiple_frames(self, frame_paths: List[str]) -> Dict[str, Any]:
        """
        複数フレームを処理して最良の結果を選択
        """
        results = []
        
        for frame_path in frame_paths[:5]:  # 最大5フレーム処理
            result = self.process_receipt(frame_path)
            if result and result.get('confidence_score', 0) > 0.5:
                results.append(result)
        
        if not results:
            return self._basic_ocr_extraction(frame_paths[0])
        
        # 最も信頼度の高い結果を選択
        best_result = max(results, key=lambda x: x.get('confidence_score', 0))
        
        # 複数の結果から情報を統合（オプション）
        if len(results) > 1:
            # 店舗名の投票
            vendors = [r.get('vendor') for r in results if r.get('vendor')]
            if vendors:
                from collections import Counter
                vendor_counts = Counter(vendors)
                best_result['vendor'] = vendor_counts.most_common(1)[0][0]
            
            # 金額の平均または最頻値
            totals = [r.get('total') for r in results if r.get('total')]
            if totals:
                # 外れ値を除外して平均
                totals_sorted = sorted(totals)
                if len(totals_sorted) > 2:
                    # 上下10%を除外
                    trim_count = max(1, len(totals_sorted) // 10)
                    totals_trimmed = totals_sorted[trim_count:-trim_count] if trim_count < len(totals_sorted) // 2 else totals_sorted
                    best_result['total'] = sum(totals_trimmed) / len(totals_trimmed)
        
        return best_result