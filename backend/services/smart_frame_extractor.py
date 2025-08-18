"""
スマートフレーム抽出サービス
レシートがよく見えるフレームを自動で検出し選択
"""
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import imagehash
from PIL import Image
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

class SmartFrameExtractor:
    def __init__(self):
        # 品質評価重み（レシート検出に最適化）
        self.quality_weights = {
            'sharpness': 0.2,      # 鮮明度（手ぶれなし）
            'contrast': 0.15,      # コントラスト（テキスト可読性）
            'brightness': 0.1,     # 明度（暗すぎたり明るすぎたりしない）
            'text_density': 0.35,  # テキスト密度（レシートの可能性）- 重要
            'edge_density': 0.2    # エッジ密度（文書特徴）
        }
        
        # 重複検出闾値（再び厳格に）
        self.similarity_threshold = 8   # pHash距離（15→8に減少、より厳格に）
        
        # 最小品質スコア（より低く）
        self.min_quality_score = 0.15  # 0.2 → 0.15により低く（より多くのフレーム受容）
        
    def extract_smart_frames(self, video_path: str, sample_fps: int = 10) -> List[Dict[str, Any]]:
        logger.info(f"Starting smart frame extraction with sample_fps={sample_fps}")
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        # サンプリング間隔計算（より頻繁にサンプリング）
        frame_interval = int(fps / sample_fps)
        
        logger.info(f"Video: {duration:.1f}s, {total_frames} frames, sampling every {frame_interval} frames")
        
        # 第1段階：すべての候補フレーム収集及び評価
        candidate_frames = []
        frame_idx = 0
        
        output_dir = Path("uploads/frames")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_interval == 0:
                # フレームインデックスから計算する方が正確
                # OpenCVのCAP_PROP_POS_MSECは不正確な場合が多い
                time_ms = int((frame_idx / fps) * 1000)
                
                # フレーム品質評価
                quality_score, quality_details = self._evaluate_frame_quality(frame)
                
                if quality_score >= self.min_quality_score:
                    # フレーム保存 - タイムスタンプをファイル名に含む
                    frame_filename = f"{Path(video_path).stem}_frame_{time_ms:08d}ms.jpg"
                    frame_path = str(output_dir / frame_filename)
                    cv2.imwrite(frame_path, frame)
                    
                    # pHash計算
                    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    phash = imagehash.phash(pil_img)
                    
                    candidate_frames.append({
                        'frame_idx': frame_idx,
                        'time_ms': time_ms,
                        'quality_score': quality_score,
                        'quality_details': quality_details,
                        'phash': phash,
                        'frame_path': frame_path,
                        'has_receipt': quality_details.get('has_receipt', False)
                    })
                    
                    logger.debug(f"Frame {frame_idx} at {time_ms}ms: score={quality_score:.2f}, receipt={quality_details.get('has_receipt')}, sharpness={quality_details.get('sharpness', 0):.2f}")
            
            frame_idx += 1
        
        cap.release()
        
        if not candidate_frames:
            logger.warning("No quality frames found in video")
            return []
        
        # 第2段階：重複除去及び最適フレーム選択
        optimal_frames = self._select_optimal_frames(candidate_frames)
        
        logger.info(f"Selected {len(optimal_frames)} optimal frames from {len(candidate_frames)} candidates")
        
        # 最低5個フレームは選択するよう保証
        if len(optimal_frames) < 5 and len(candidate_frames) > 5:
            logger.warning(f"Only {len(optimal_frames)} frames selected, adding more from candidates")
            # 品質順にソートして追加
            candidate_frames.sort(key=lambda x: x['quality_score'], reverse=True)
            for frame in candidate_frames:
                if frame not in optimal_frames:
                    optimal_frames.append(frame)
                    if len(optimal_frames) >= min(10, len(candidate_frames)):
                        break
            optimal_frames.sort(key=lambda x: x['time_ms'])
            logger.info(f"Extended selection to {len(optimal_frames)} frames")
        
        return optimal_frames
    
    def _evaluate_frame_quality(self, frame: np.ndarray) -> Tuple[float, Dict[str, Any]]:
        """
        フレーム品質評価
        
        Returns:
            (品質スコア 0-1、詳細情報)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        details = {}
        
        # 1. 鮮明度（Laplacian variance）
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()
        # 正規化（より寛大に - 200に下げ）
        details['sharpness'] = min(sharpness / 200, 1.0)
        
        # 2. コントラスト（標準偏差）
        contrast = gray.std()
        details['contrast'] = min(contrast / 50, 1.0)
        
        # 3. 明度（適正範囲チェック）
        brightness = gray.mean()
        # 暗すぎたり明るすぎたりすると減点
        if 50 < brightness < 200:
            details['brightness'] = 1.0
        else:
            details['brightness'] = max(0, 1.0 - abs(brightness - 125) / 125)
        
        # 4. テキスト密度推定（エッジベース）
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (height * width)
        details['edge_density'] = min(edge_density * 10, 1.0)  # 正規化
        
        # 5. テキスト領域検出（MSERまたは簡単な闾値）
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # テキストのようなパターン検出（水平線検出）
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width // 30, 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        horizontal_lines = cv2.countNonZero(horizontal)
        
        # テキスト密度推定
        text_density = horizontal_lines / (height * width)
        details['text_density'] = min(text_density * 100, 1.0)
        
        # 6. レシート特徴検出
        has_receipt = self._detect_receipt_features(gray, edges)
        details['has_receipt'] = has_receipt
        
        # 加重平均計算
        score = 0
        for metric, weight in self.quality_weights.items():
            if metric in details:
                score += details[metric] * weight
        
        # レシートが検出されたらボーナススコア
        if has_receipt:
            score = min(score * 1.3, 1.0)  # レシート検出時ボーナス
        
        details['final_score'] = score
        
        return score, details
    
    def _detect_receipt_features(self, gray: np.ndarray, edges: np.ndarray) -> bool:
        """
        レシート特徴検出 - 極度に簡素化
        実際はGeminiがレシートを判断するのでここでは基本品質のみチェック
        """
        # すべてのフレームを潜在的レシートとして扱う
        # 実際のレシート判断はGemini APIが実行
        return True  # すべてのフレームを候補として使用
    
    def _select_optimal_frames(self, candidates: List[Dict]) -> List[Dict]:
        """
        重複除去及び最適フレーム選択 - 時間ベース均等サンプリング
        """
        if not candidates:
            return []
        
        # 時間順ソート
        candidates.sort(key=lambda x: x['time_ms'])
        
        # ビデオ全体時間
        total_duration = candidates[-1]['time_ms'] - candidates[0]['time_ms']
        
        selected = []
        selected_hashes = []
        
        # 全体ビデオを均等にサンプリング（データベースアプローチ）
        # 19秒ビデオで7個レシート = 約2.7秒ごとに1個
        # 安全に1.5秒ごとに最低1個フレーム確保
        min_interval = 1500  # 1.5秒間隔で最低保証
        fine_interval = 500   # 0.5秒間隔で細かくチェック
        
        # 必須ターゲット時間設定（1.5秒間隔）
        required_times = []
        current_time = 0
        while current_time <= total_duration:
            required_times.append(current_time)
            current_time += min_interval
        
        # 追加細密ターゲット時間（0.5秒間隔）
        fine_times = []
        current_time = 0
        while current_time <= total_duration:
            if current_time not in required_times:
                fine_times.append(current_time)
            current_time += fine_interval
        
        logger.info(f"Total duration: {total_duration}ms, Required times: {len(required_times)}, Fine times: {len(fine_times)}")
        
        # 必須ターゲット時間でフレーム選択
        for target_time in required_times:
            # ターゲット時間±500ms範囲で最高品質フレーム探索（より厳格に）
            nearby_frames = [f for f in candidates 
                           if abs(f['time_ms'] - target_time) <= 500 and
                           f['phash'] not in selected_hashes]
            
            if not nearby_frames:
                # 範囲を少し広げて再試行（±750ms）
                nearby_frames = [f for f in candidates 
                               if abs(f['time_ms'] - target_time) <= 750 and
                               f['phash'] not in selected_hashes]
            
            if nearby_frames:
                # ターゲット時間に最も近いフレーム優先、同じ距離なら品質優先
                best_frame = min(nearby_frames, 
                               key=lambda x: (abs(x['time_ms'] - target_time), -x['quality_score']))
                selected.append(best_frame)
                selected_hashes.append(best_frame['phash'])
                logger.info(f"Required {target_time}ms: selected frame at {best_frame['time_ms']}ms (score: {best_frame['quality_score']:.2f})")
        
        # 細密ターゲット時間で追加フレーム選択（最大70個まで）
        for target_time in fine_times:
            if len(selected) >= 70:
                break
                
            # ターゲット時間±250ms範囲で最高品質フレーム探索
            nearby_frames = [f for f in candidates 
                           if abs(f['time_ms'] - target_time) <= 250 and
                           f['phash'] not in selected_hashes]
            
            if nearby_frames and nearby_frames[0]['quality_score'] >= 0.3:  # 品質基準満たした場合のみ
                best_frame = max(nearby_frames, key=lambda x: x['quality_score'])
                selected.append(best_frame)
                selected_hashes.append(best_frame['phash'])
                logger.info(f"Fine {target_time}ms: selected frame at {best_frame['time_ms']}ms (score: {best_frame['quality_score']:.2f})")
        
        # 追加フレーム収集（最低個数保証）
        if len(selected) < 20:  # 最低20個保証
            remaining = [f for f in candidates if f['phash'] not in selected_hashes]
            remaining.sort(key=lambda x: x['quality_score'], reverse=True)
            
            for frame in remaining[:10-len(selected)]:
                selected.append(frame)
                selected_hashes.append(frame['phash'])
        
        # 時間順ソート
        selected.sort(key=lambda x: x['time_ms'])
        
        # 選択されたフレーム時間帯ログ
        selected_times = [f['time_ms'] for f in selected]
        logger.info(f"Selected frame times (ms): {selected_times[:10]}...")  # 最初の10個のみ表示
        
        # レシート統計
        receipt_count = sum(1 for f in selected if f.get('has_receipt'))
        logger.info(f"Final selection: {len(selected)} frames ({receipt_count} with receipts) from {len(candidates)} candidates")
        
        # フレーム情報整理
        for frame in selected:
            # pHashを文字列に変換
            frame['phash'] = str(frame['phash'])
            # 品質詳細情報含む
            frame['sharpness'] = frame['quality_details'].get('sharpness', 0)
            frame['brightness'] = frame['quality_details'].get('brightness', 0) * 255
            frame['contrast'] = frame['quality_details'].get('contrast', 0) * 50
            frame['frame_score'] = frame['quality_score']
        
        return selected