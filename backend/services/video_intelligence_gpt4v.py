"""
GPT-4V統合版 Video Intelligence Service
全てのOCR処理をGPT-4Vに統一
"""
import cv2
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

class VideoIntelligenceGPT4V:
    def __init__(self):
        """GPT-4V版ビデオ処理サービス初期化"""
        # GPT-4Vサービスを初期化
        try:
            from services.gpt4v_service import GPT4VisionService
            self.vision_service = GPT4VisionService()
            logger.info("✅ GPT-4V Video Intelligence Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GPT-4V service: {e}")
            raise
    
    def extract_frames(self, video_path: str, fps: int = 2) -> List[Dict[str, Any]]:
        """動画からフレームを抽出"""
        frames = []
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            logger.error(f"動画ファイルを開けません: {video_path}")
            return frames
        
        # 動画のFPSを取得
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = 30  # デフォルト値
        
        # フレーム間隔を計算
        frame_interval = int(video_fps / fps)
        frame_count = 0
        extracted_count = 0
        
        # 出力ディレクトリ作成
        base_dir = Path("/tmp") if os.getenv("RENDER") == "true" else Path("uploads")
        frames_dir = base_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 指定されたFPSでフレームを抽出
            if frame_count % frame_interval == 0:
                # フレームを保存
                timestamp_ms = int((frame_count / video_fps) * 1000)
                frame_filename = f"frame_{extracted_count:04d}_{timestamp_ms}ms.jpg"
                frame_path = frames_dir / frame_filename
                
                # JPEGとして保存（品質95で高品質維持）
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                frames.append({
                    'frame_number': extracted_count,
                    'timestamp_ms': timestamp_ms,
                    'file_path': str(frame_path)
                })
                
                extracted_count += 1
                logger.debug(f"Frame {extracted_count} extracted at {timestamp_ms}ms")
            
            frame_count += 1
        
        cap.release()
        logger.info(f"✅ Extracted {len(frames)} frames from video")
        return frames
    
    def detect_receipts_in_frames(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        フレームから領収書を検出（GPT-4V使用）
        簡易的な検出: 各フレームをGPT-4Vで分析
        """
        receipts = []
        
        for frame in frames:
            frame_path = frame['file_path']
            
            # GPT-4Vで領収書を抽出
            try:
                result = self.vision_service.extract_receipt(frame_path)
                
                if result and result.get('vendor'):
                    # 領収書が検出された
                    receipt_data = {
                        'frame_number': frame['frame_number'],
                        'timestamp_ms': frame['timestamp_ms'],
                        'image_path': frame_path,
                        'receipt_data': result,
                        'confidence': result.get('confidence', 0.95)
                    }
                    receipts.append(receipt_data)
                    logger.info(f"✅ Receipt detected in frame {frame['frame_number']}: {result.get('vendor')}")
                    
            except Exception as e:
                logger.debug(f"Frame {frame['frame_number']} - No receipt detected or error: {e}")
                continue
        
        logger.info(f"✅ Total receipts detected: {len(receipts)}")
        return receipts
    
    def select_best_frames(self, frames: List[Dict[str, Any]], max_frames: int = 10) -> List[Dict[str, Any]]:
        """
        最適なフレームを選択（品質ベース）
        """
        selected_frames = []
        
        for frame in frames[:max_frames]:  # 最初のN枚を選択
            frame_path = frame['file_path']
            
            # 画像品質チェック
            img = cv2.imread(frame_path)
            if img is None:
                continue
            
            # ブラー検出（シャープネスチェック）
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # シャープネススコアが閾値以上なら選択
            if laplacian_var > 100:  # 閾値は調整可能
                frame['quality_score'] = laplacian_var
                selected_frames.append(frame)
        
        # 品質スコアでソート
        selected_frames.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        
        return selected_frames[:max_frames]
    
    async def analyze_video(self, video_path: str, video_id: int, db) -> Dict[str, Any]:
        """
        動画全体を分析してレシートを抽出（GPT-4V使用）
        """
        try:
            logger.info(f"Starting GPT-4V video analysis for video {video_id}")
            
            # 1. フレーム抽出
            frames = self.extract_frames(video_path, fps=1)  # 1秒に1フレーム
            
            if not frames:
                logger.error("No frames extracted from video")
                return {'success': False, 'error': 'No frames extracted'}
            
            # 2. 最適なフレームを選択
            selected_frames = self.select_best_frames(frames, max_frames=10)
            
            # 3. GPT-4Vで領収書検出
            receipts = self.detect_receipts_in_frames(selected_frames)
            
            # 4. 結果を返す
            return {
                'success': True,
                'total_frames': len(frames),
                'analyzed_frames': len(selected_frames),
                'receipts_found': len(receipts),
                'receipts': receipts
            }
            
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def extract_single_frame_receipt(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        単一画像から領収書データを抽出（GPT-4V使用）
        既存のOCRメソッドとの互換性のため
        """
        try:
            result = self.vision_service.extract_receipt(image_path)
            return result
        except Exception as e:
            logger.error(f"Failed to extract receipt from image: {e}")
            return None

# 既存コードとの互換性のためのエイリアス
VideoAnalyzer = VideoIntelligenceGPT4V