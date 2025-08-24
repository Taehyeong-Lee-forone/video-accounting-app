import os
import logging
import re
from typing import List, Dict, Any, Optional
from google.cloud import videointelligence
from google.cloud import storage
import google.generativeai as genai
import json
import cv2
import numpy as np
import imagehash
from PIL import Image
import ffmpeg
from pathlib import Path
import hashlib
from rapidfuzz import fuzz
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.japanese_date import parse_japanese_date, is_japanese_era_date

logger = logging.getLogger(__name__)

class VideoAnalyzer:
    def __init__(self):
        try:
            # プロダクション（Cloud Runなど）では自動で認証
            # ローカルではGOOGLE_APPLICATION_CREDENTIALS環境変数使用
            if os.getenv("K_SERVICE") or os.getenv("GAE_ENV"):
                # Cloud Run、App Engine環境 - 自動認証
                self.video_client = videointelligence.VideoIntelligenceServiceClient()
                self.storage_client = storage.Client()
            else:
                # ローカル環境 - キーファイル必要
                self.video_client = videointelligence.VideoIntelligenceServiceClient()
                self.storage_client = storage.Client()
        except Exception as e:
            logger.warning(f"Google Cloud clients could not be initialized: {e}")
            self.video_client = None
            self.storage_client = None
        
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key and gemini_api_key != "your-gemini-api-key-here":
            try:
                genai.configure(api_key=gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                logger.warning(f"Gemini model could not be initialized: {e}")
                self.gemini_model = None
        else:
            self.gemini_model = None
        
    def extract_frames(self, video_path: str, fps: int = 2) -> List[Dict[str, Any]]:
        """動画からフレームを抽出 - スマート抽出モード"""
        try:
            # スマート抽出を試みる
            from services.smart_frame_extractor import SmartFrameExtractor
            
            logger.info("Using smart frame extraction for better receipt detection")
            extractor = SmartFrameExtractor()
            
            # 初期サンプリングは多めに（fps=10）、その後フィルタリング
            frames = extractor.extract_smart_frames(video_path, sample_fps=10)
            
            if frames:
                logger.info(f"Smart extraction found {len(frames)} optimal frames")
                return frames
            else:
                logger.warning("No optimal frames found, falling back to interval extraction")
                
        except Exception as e:
            logger.warning(f"Smart extraction failed: {e}, falling back to interval extraction")
        
        # フォールバック: 従来の固定間隔抽出
        return self._extract_frames_interval(video_path, fps)
    
    def _extract_frames_interval(self, video_path: str, fps: int = 2) -> List[Dict[str, Any]]:
        """従来の固定間隔フレーム抽出（フォールバック用）"""
        frames = []
        output_dir = Path("uploads/frames")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])
            
            # ffmpegでフレーム抽出 - タイムスタンプ付き
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.filter(stream, 'fps', fps=fps)
            
            pattern = str(output_dir / f"{Path(video_path).stem}_frame_%04d.jpg")
            stream = ffmpeg.output(stream, pattern, **{'q:v': 2})
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            # 抽出されたフレームを処理
            frame_files = sorted(output_dir.glob(f"{Path(video_path).stem}_frame_*.jpg"))
            
            # 実際のフレーム間隔（ミリ秒）
            actual_frame_interval_ms = 1000 / fps  # fps=2の場合、500ms間隔
            
            for idx, frame_file in enumerate(frame_files):
                # 正確なタイムスタンプ計算 - ffmpegのfpsフィルタを使用した場合
                # フレーム番号から実際の時間を計算
                time_ms = int((idx / fps) * 1000)  # idx番目のフレーム / fps * 1000ms
                frame_data = self._analyze_frame(str(frame_file), time_ms)
                frames.append(frame_data)
                
            return frames
            
        except Exception as e:
            logger.error(f"フレーム抽出エラー: {e}")
            raise
    
    def _analyze_frame(self, frame_path: str, time_ms: int) -> Dict[str, Any]:
        """フレームの品質分析"""
        img = cv2.imread(frame_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # シャープネス（ラプラシアン分散）
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()
        
        # 明るさとコントラスト
        brightness = np.mean(gray)
        contrast = np.std(gray)
        
        # pHash計算
        pil_img = Image.open(frame_path)
        phash = str(imagehash.phash(pil_img))
        
        # スコア計算（正規化）
        sharpness_norm = min(sharpness / 1000, 1.0)
        brightness_norm = 1.0 - abs(brightness - 128) / 128
        contrast_norm = min(contrast / 50, 1.0)
        
        frame_score = (sharpness_norm * 0.5 + brightness_norm * 0.25 + contrast_norm * 0.25)
        
        return {
            'time_ms': time_ms,
            'frame_path': frame_path,
            'sharpness': sharpness,
            'brightness': brightness,
            'contrast': contrast,
            'phash': phash,
            'frame_score': frame_score
        }
    
    async def analyze_video_text(self, video_path: str) -> Dict[str, Any]:
        """Gemini Vision APIでテキスト検出"""
        # Google Vision APIの代わりにGeminiを使用してフレームから直接テキスト抽出
        logger.info("Gemini Vision APIを使用してOCR処理")
        return {
            'input_uri': video_path,
            'text_annotations': [
                {
                    'text': '',  # Geminiがフレームごとに処理
                    'segments': [
                        {
                            'start_time_ms': 0,
                            'end_time_ms': 5000,
                            'confidence': 0.95,
                            'frames': []
                        }
                    ]
                }
            ]
        }
        
        try:
            # GCSにアップロード（必要な場合）
            if video_path.startswith('gs://'):
                input_uri = video_path
            else:
                # ローカルファイルの場合はGCSにアップロード
                bucket_name = os.getenv("GCS_BUCKET")
                blob_name = f"videos/{Path(video_path).name}"
                bucket = self.storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(video_path)
                input_uri = f"gs://{bucket_name}/{blob_name}"
            
            # テキスト検出リクエスト
            features = [videointelligence.Feature.TEXT_DETECTION]
            config = videointelligence.TextDetectionConfig(
                language_hints=["ja", "en"]
            )
            video_context = videointelligence.VideoContext(
                text_detection_config=config
            )
            
            operation = self.video_client.annotate_video(
                request={
                    "input_uri": input_uri,
                    "features": features,
                    "video_context": video_context,
                }
            )
            
            logger.info("Video Intelligence API処理中...")
            result = operation.result(timeout=300)
            
            # テキスト注釈の処理
            text_annotations = []
            for annotation in result.annotation_results[0].text_annotations:
                text_data = {
                    'text': annotation.text,
                    'segments': []
                }
                
                for segment in annotation.segments:
                    segment_data = {
                        'start_time_ms': int(segment.segment.start_time_offset.total_seconds() * 1000),
                        'end_time_ms': int(segment.segment.end_time_offset.total_seconds() * 1000),
                        'confidence': segment.confidence,
                        'frames': []
                    }
                    
                    for frame in segment.frames:
                        frame_data = {
                            'time_ms': int(frame.time_offset.total_seconds() * 1000),
                            'vertices': [
                                {'x': v.x, 'y': v.y} 
                                for v in frame.rotated_bounding_box.vertices
                            ]
                        }
                        segment_data['frames'].append(frame_data)
                    
                    text_data['segments'].append(segment_data)
                
                text_annotations.append(text_data)
            
            return {
                'input_uri': input_uri,
                'text_annotations': text_annotations
            }
            
        except Exception as e:
            logger.error(f"Video Intelligence APIエラー: {e}")
            raise
    
    async def extract_receipt_data(self, image_path: str, ocr_text: str) -> Dict[str, Any]:
        """レシートデータ抽出 - Vision APIのみ使用"""
        
        # Vision APIを使用
        try:
            from services.vision_ocr import VisionOCRService
            vision_service = VisionOCRService()
            logger.info("Using Vision API for OCR")
            result = await vision_service.extract_receipt_data(image_path)
            if result and result.get('vendor') != 'OCR Failed':
                return result
            else:
                logger.error("Vision API failed to extract receipt data")
                raise Exception("Vision API failed to extract receipt data")
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            raise Exception(f"Vision API error: {e}")
    
    def generate_receipt_fingerprint(self, receipt_data: Dict) -> str:
        """レシート固有フィンガープリント生成 - コア要素だけでユニークな識別子を生成"""
        if not receipt_data:
            return ""
        
        # コア識別要素を組み合わせ
        elements = []
        
        # 1. 販売店名（正規化） - 必須
        vendor = self._normalize_text(receipt_data.get('vendor', ''))
        if not vendor:
            return ""  # 販売店名がなければフィンガープリント生成不可
        elements.append(f"v:{vendor}")
        
        # 2. 総額（小数点除去） - 必須
        total = receipt_data.get('total')
        if total and total > 0:
            elements.append(f"t:{int(total)}")
        else:
            return ""  # 金額がなければフィンガープリント生成不可
        
        # 3. 発行日（あれば含む）
        issue_date = receipt_data.get('issue_date')
        if issue_date:
            elements.append(f"d:{issue_date}")
        
        # 4. 税情報（区切りとして使用）
        tax = receipt_data.get('tax')
        if tax and tax > 0:
            elements.append(f"x:{int(tax)}")
        
        # 5. 最初の商品名（追加区切り）
        line_items = receipt_data.get('line_items', [])
        if line_items and isinstance(line_items, list) and len(line_items) > 0:
            first_item = line_items[0]
            if isinstance(first_item, dict) and first_item.get('name'):
                item_name = self._normalize_text(str(first_item['name']))[:20]  # 最大20文字
                if item_name:
                    elements.append(f"i:{item_name}")
        
        # 結合してハッシュ生成
        combined = "|".join(elements)
        
        # 短いハッシュ生成（衝突可能性を減らすために16文字に増加）
        fingerprint = hashlib.md5(combined.encode('utf-8')).hexdigest()[:16]
        logger.debug(f"Generated fingerprint: {fingerprint} from {combined}")
        return fingerprint

    def check_duplicate(self, phash: str, text: str, existing_receipts: List[Dict], 
                       current_frame_time_ms: int = None, current_receipt_data: Dict = None) -> Optional[int]:
        """インテリジェント重複検出 - 連続フレームでのみ厳格、時間差が大きい場合はフィンガープリントのみ比較"""
        
        # 0段階：レシート固有フィンガープリント比較（最も正確な方法）
        if current_receipt_data:
            current_fingerprint = self.generate_receipt_fingerprint(current_receipt_data)
            if current_fingerprint:
                for receipt in existing_receipts:
                    # 既存レシートのフィンガープリント生成
                    existing_fingerprint = self.generate_receipt_fingerprint({
                        'vendor': receipt.get('vendor'),
                        'total': receipt.get('total'),
                        'issue_date': receipt.get('issue_date'),
                        'tax': receipt.get('tax'),
                    })
                    
                    # フィンガープリントが同一の場合のみ時間チェック
                    if current_fingerprint == existing_fingerprint and existing_fingerprint:
                        # 時間差が大きい場合（10秒以上）は別のレシートとして扱う
                        if current_frame_time_ms is not None and receipt.get('time_ms') is not None:
                            time_diff = abs(current_frame_time_ms - receipt['time_ms'])
                            if time_diff > 10000:  # 10秒以上差があれば別のレシート
                                logger.info(f"Same fingerprint but different time: {time_diff}ms apart, treating as different receipt")
                                continue
                        
                        logger.info(f"Fingerprint duplicate detected: {current_fingerprint}")
                        return receipt['id']
        
        # 1段階：連続フレームでのみ時間+内容重複チェック（1秒以内）
        if current_frame_time_ms is not None:
            for receipt in existing_receipts:
                if receipt.get('time_ms') is not None:
                    time_diff = abs(current_frame_time_ms - receipt['time_ms'])
                    # 1秒以内の連続フレームでのみ内容比較
                    if time_diff <= 1000:  # 1秒 = 1,000ms（連続フレームのみ）
                        # 内容比較 - vendor、total、dateすべて同じでなければ重複ではない
                        if (current_receipt_data and 
                            current_receipt_data.get('vendor') == receipt.get('vendor') and
                            current_receipt_data.get('issue_date') == receipt.get('issue_date') and
                            abs((current_receipt_data.get('total', 0) or 0) - (receipt.get('total', 0) or 0)) < 0.01):
                            logger.info(f"Time+Content duplicate: {time_diff}ms apart, same vendor+date+amount")
                            return receipt['id']
        
        # 2段階：pHashベースの重複検出（非常に厳格）
        normalized = self._normalize_text(text)
        text_hash = hashlib.md5(normalized.encode()).hexdigest()
        
        for receipt in existing_receipts:
            if not receipt.get('phash'):
                continue
                
            try:
                distance = imagehash.hex_to_hash(phash) - imagehash.hex_to_hash(receipt['phash'])
                
                # 完全に同一の画像のみ重複処理（pHash距離0）
                if distance == 0:
                    logger.info(f"Identical image duplicate: phash distance={distance}")
                    return receipt['id']
                
                # ほぼ同一の画像（pHash距離1-2）+ 内容確認
                elif distance <= 2:
                    if (current_receipt_data and receipt.get('vendor') and receipt.get('total') and
                        current_receipt_data.get('vendor') == receipt.get('vendor') and
                        abs((current_receipt_data.get('total', 0) or 0) - (receipt.get('total', 0) or 0)) < 1):
                        logger.info(f"Very similar image + same content: distance={distance}")
                        return receipt['id']
                
                # OCRテキスト類似度が非常に高い場合（95%以上）
                elif distance <= 5:  # 画像は少し違う可能性があるが
                    if existing_receipt_text_hash := receipt.get('normalized_text_hash'):
                        similarity = fuzz.ratio(text_hash, existing_receipt_text_hash)
                        if similarity >= 95:  # 95%以上テキスト類似
                            logger.info(f"High text similarity: {similarity}% with image distance={distance}")
                            return receipt['id']
                        
            except Exception as e:
                logger.warning(f"Error comparing phash: {e}")
        
        return None
    
    def _check_content_similarity(self, current_data: Dict, existing_receipt: Dict, current_text_hash: str) -> bool:
        """内容ベースの類似性検査"""
        if not current_data:
            # 内容データがなければテキストのみ比較
            if existing_receipt.get('normalized_text_hash'):
                similarity = fuzz.ratio(current_text_hash, existing_receipt['normalized_text_hash'])
                return similarity >= 90
            return False
        
        # ベンダー名 + 金額一致チェック
        vendor_match = (current_data.get('vendor') and 
                       existing_receipt.get('vendor') and
                       current_data.get('vendor') == existing_receipt.get('vendor'))
        
        amount_match = (current_data.get('total') and 
                       existing_receipt.get('total') and
                       abs(current_data.get('total') - existing_receipt.get('total')) < 0.01)
        
        # ベンダー名と金額が両方一致すれば重複の可能性が高い
        if vendor_match and amount_match:
            return True
            
        # テキスト類似度も考慮
        if existing_receipt.get('normalized_text_hash'):
            similarity = fuzz.ratio(current_text_hash, existing_receipt['normalized_text_hash'])
            if similarity >= 85:
                return True
                
        return False
    
    def _normalize_text(self, text: str) -> str:
        """テキスト正規化"""
        if not text:
            return ""
        
        # 全角を半角に変換
        text = text.translate(str.maketrans(
            '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
            '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        ))
        
        # スペース、記号を削除
        import re
        text = re.sub(r'[^\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '', text)
        
        return text.lower()
    
    def select_best_frame(self, frames: List[Dict]) -> Dict:
        """ベストフレーム選定"""
        if not frames:
            return None
        
        # OCRテキスト量を考慮したスコア再計算
        for frame in frames:
            ocr_weight = min(len(frame.get('ocr_text', '')) / 500, 1.0)
            frame['final_score'] = frame['frame_score'] * 0.7 + ocr_weight * 0.3
        
        # 最高スコアのフレームを選択
        best_frame = max(frames, key=lambda x: x.get('final_score', 0))
        return best_frame