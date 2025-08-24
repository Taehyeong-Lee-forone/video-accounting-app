"""
Non-Maximum Suppression (NMS) implementations for frame selection.
"""

import numpy as np
import logging
from typing import List, Tuple, Set
from collections import defaultdict
import imagehash
from PIL import Image
from sklearn.cluster import DBSCAN
from .types import FrameCandidate, Config

logger = logging.getLogger(__name__)


class NMSProcessor:
    """
    # 複数のNMS戦略を組み合わせたフレーム選択
    Multiple NMS strategies for optimal frame selection.
    """
    
    def __init__(self, config: Config):
        self.config = config
        
    def apply_temporal_nms(self, candidates: List[FrameCandidate], 
                          window_s: float = None) -> List[FrameCandidate]:
        """
        # 時間ウィンドウ内で最高スコアのフレームを選択
        Apply temporal NMS to select best frames within time windows.
        
        Args:
            candidates: List of frame candidates sorted by time
            window_s: Time window in seconds (default from config)
            
        Returns:
            Filtered list of candidates
        """
        if not candidates:
            return []
            
        window_s = window_s or self.config.temporal_window
        selected = []
        
        # グループ化：時間ウィンドウごと
        time_groups = defaultdict(list)
        for cand in candidates:
            window_idx = int(cand.time_s / window_s)
            time_groups[window_idx].append(cand)
        
        # 各ウィンドウから最高スコアを選択
        for window_idx in sorted(time_groups.keys()):
            group = time_groups[window_idx]
            # スコアでソート（降順）
            group.sort(key=lambda x: x.total_score, reverse=True)
            selected.append(group[0])
            
            # デバッグ情報
            if self.config.debug:
                logger.info(f"Window {window_idx} ({window_idx*window_s:.1f}s-{(window_idx+1)*window_s:.1f}s): "
                          f"Selected frame at {group[0].time_s:.2f}s with score {group[0].total_score:.3f}")
        
        logger.info(f"Temporal NMS: {len(candidates)} -> {len(selected)} frames")
        return selected
    
    def apply_visual_nms(self, candidates: List[FrameCandidate], 
                        eps: int = None) -> List[FrameCandidate]:
        """
        # 視覚的類似度によるNMS（pHash + DBSCAN）
        Apply visual NMS using perceptual hashing and clustering.
        
        Args:
            candidates: List of frame candidates
            eps: Maximum Hamming distance for clustering (default from config)
            
        Returns:
            Filtered list of visually distinct candidates
        """
        if not candidates:
            return []
            
        eps = eps or self.config.visual_eps
        
        # pHashを計算（既に計算済みでない場合）
        for cand in candidates:
            if cand.phash is None:
                cand.phash = self._calculate_phash(cand.frame_path)
        
        # ハミング距離行列を構築
        n = len(candidates)
        distances = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                if candidates[i].phash and candidates[j].phash:
                    dist = self._hamming_distance(candidates[i].phash, candidates[j].phash)
                    distances[i, j] = dist
                    distances[j, i] = dist
        
        # DBSCANクラスタリング
        clustering = DBSCAN(eps=eps, min_samples=1, metric='precomputed')
        labels = clustering.fit_predict(distances)
        
        # 各クラスターから最高スコアを選択
        selected = []
        clusters = defaultdict(list)
        
        for idx, label in enumerate(labels):
            clusters[label].append(candidates[idx])
        
        for cluster_id in sorted(clusters.keys()):
            cluster = clusters[cluster_id]
            # スコアでソート
            cluster.sort(key=lambda x: x.total_score, reverse=True)
            selected.append(cluster[0])
            
            if self.config.debug:
                logger.info(f"Visual cluster {cluster_id}: "
                          f"Selected frame at {cluster[0].time_s:.2f}s from {len(cluster)} similar frames")
        
        logger.info(f"Visual NMS: {len(candidates)} -> {len(selected)} frames")
        return selected
    
    def apply_combined_nms(self, candidates: List[FrameCandidate]) -> List[FrameCandidate]:
        """
        # 時間的NMSと視覚的NMSを組み合わせる
        Apply both temporal and visual NMS in sequence.
        
        Returns:
            Final filtered list of candidates
        """
        # まず時間的NMS
        candidates = self.apply_temporal_nms(candidates)
        
        # 次に視覚的NMS
        candidates = self.apply_visual_nms(candidates)
        
        return candidates
    
    def apply_text_deduplication(self, candidates: List[FrameCandidate], 
                                threshold: float = None) -> List[FrameCandidate]:
        """
        # テキスト類似度による重複除去（Jaccard/トークン類似度）
        Remove duplicate frames based on OCR text similarity.
        
        Args:
            candidates: List of candidates with OCR text
            threshold: Similarity threshold (default from config)
            
        Returns:
            Deduplicated list of candidates
        """
        if not candidates:
            return []
            
        threshold = threshold or self.config.text_jaccard_threshold
        selected = []
        seen_texts = []
        
        for cand in candidates:
            if not cand.ocr_text:
                # OCRテキストがない場合は保持
                selected.append(cand)
                continue
            
            # トークン化
            tokens = set(cand.ocr_text.lower().split())
            
            # 既存のテキストと比較
            is_duplicate = False
            for seen_tokens in seen_texts:
                # Jaccard類似度
                intersection = len(tokens & seen_tokens)
                union = len(tokens | seen_tokens)
                
                if union > 0:
                    jaccard = intersection / union
                    if jaccard > threshold:
                        is_duplicate = True
                        if self.config.debug:
                            logger.info(f"Text duplicate found: {jaccard:.2f} similarity")
                        break
            
            if not is_duplicate:
                selected.append(cand)
                seen_texts.append(tokens)
        
        logger.info(f"Text deduplication: {len(candidates)} -> {len(selected)} frames")
        return selected
    
    def apply_adaptive_selection(self, candidates: List[FrameCandidate], 
                                relaxation_steps: int = 3) -> List[FrameCandidate]:
        """
        # 目標フレーム数に合わせて閾値を調整
        Adaptively select frames to meet target count.
        
        Args:
            candidates: List of all candidates
            relaxation_steps: Number of threshold relaxation attempts
            
        Returns:
            Selected frames meeting target count
        """
        selected = candidates.copy()
        
        # 初期NMS適用
        selected = self.apply_combined_nms(selected)
        
        # 目標範囲チェック
        if self.config.target_min <= len(selected) <= self.config.target_max:
            return selected
        
        # 閾値緩和による調整
        for step in range(relaxation_steps):
            if len(selected) < self.config.target_min:
                # 閾値を緩める（より多くのフレームを選択）
                logger.info(f"Relaxing thresholds (step {step+1}): {len(selected)} < {self.config.target_min}")
                
                # 時間ウィンドウを縮小
                window = self.config.temporal_window * (0.8 ** (step+1))
                selected = self.apply_temporal_nms(candidates, window_s=window)
                
                # 視覚的閾値を緩和
                eps = self.config.visual_eps + step + 1
                selected = self.apply_visual_nms(selected, eps=eps)
                
            elif len(selected) > self.config.target_max:
                # より厳しく選択（スコアでカット）
                logger.info(f"Tightening selection (step {step+1}): {len(selected)} > {self.config.target_max}")
                selected.sort(key=lambda x: x.total_score, reverse=True)
                selected = selected[:self.config.target_max]
                break
            
            if self.config.target_min <= len(selected) <= self.config.target_max:
                break
        
        # 最終調整
        if len(selected) < self.config.target_min:
            # 最低限のフレーム数を確保（スコア順）
            all_sorted = sorted(candidates, key=lambda x: x.total_score, reverse=True)
            selected = all_sorted[:self.config.target_min]
            logger.warning(f"Could not meet target with NMS, selecting top {self.config.target_min} by score")
        
        logger.info(f"Adaptive selection: Final count = {len(selected)} frames")
        return selected
    
    def _calculate_phash(self, image_path: str, hash_size: int = 8) -> str:
        """
        # perceptual hashを計算
        Calculate perceptual hash for an image.
        """
        try:
            img = Image.open(image_path)
            return str(imagehash.phash(img, hash_size=hash_size))
        except Exception as e:
            logger.error(f"Error calculating pHash for {image_path}: {e}")
            return None
    
    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        # ハミング距離を計算
        Calculate Hamming distance between two hashes.
        """
        if not hash1 or not hash2:
            return 64  # Maximum distance
        
        # Convert hex strings to binary
        try:
            int1 = int(hash1, 16)
            int2 = int(hash2, 16)
            xor = int1 ^ int2
            return bin(xor).count('1')
        except:
            return 64
    
    def _calculate_dhash(self, image_path: str, hash_size: int = 8) -> str:
        """
        # difference hashを計算（オプション）
        Calculate difference hash for an image.
        """
        try:
            img = Image.open(image_path)
            return str(imagehash.dhash(img, hash_size=hash_size))
        except Exception as e:
            logger.error(f"Error calculating dHash for {image_path}: {e}")
            return None