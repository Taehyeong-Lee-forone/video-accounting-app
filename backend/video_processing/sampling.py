"""
Adaptive frame sampling with motion detection and stability analysis.
"""

import cv2
import numpy as np
import logging
from typing import List, Optional, Tuple
from pathlib import Path
from .types import FrameCandidate, Config

logger = logging.getLogger(__name__)


class AdaptiveSampler:
    """
    Advanced frame sampling with dual-pass extraction and stability analysis.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.prev_frame = None
        self.prev_gray = None
        
    def sample_frames(self, video_path: str) -> List[FrameCandidate]:
        """
        Extract frames using base + offset sampling with stability filtering.
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of candidate frames with basic metadata
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Video: {duration:.1f}s, {total_frames} frames, {fps:.1f} fps")
        
        # Calculate sampling intervals
        base_interval = int(fps / self.config.base_fps)
        offset_interval = int(fps / self.config.offset_fps)
        offset_frames = int(self.config.offset_shift * fps)
        
        candidates = []
        output_dir = Path("uploads/frames")
        output_dir.mkdir(parents=True, exist_ok=True)
        video_name = Path(video_path).stem
        
        # Pass 1: Base sampling
        candidates.extend(self._sample_pass(
            cap, video_name, output_dir, 
            start_frame=0, 
            interval=base_interval,
            pass_name="base"
        ))
        
        # Pass 2: Offset sampling
        cap.set(cv2.CAP_PROP_POS_FRAMES, offset_frames)
        candidates.extend(self._sample_pass(
            cap, video_name, output_dir,
            start_frame=offset_frames,
            interval=offset_interval,
            pass_name="offset"
        ))
        
        cap.release()
        
        # Sort by time
        candidates.sort(key=lambda x: x.time_ms)
        
        # Remove near-duplicates (within 50ms)
        filtered = []
        last_time = -1000
        for cand in candidates:
            if cand.time_ms - last_time >= 50:
                filtered.append(cand)
                last_time = cand.time_ms
        
        logger.info(f"Sampled {len(filtered)} frames from {len(candidates)} total")
        return filtered
    
    def _sample_pass(self, cap: cv2.VideoCapture, video_name: str, 
                     output_dir: Path, start_frame: int, 
                     interval: int, pass_name: str) -> List[FrameCandidate]:
        """Single sampling pass."""
        candidates = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_idx = start_frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        
        while frame_idx < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate stability/motion score
            motion_score = self._calculate_motion(frame)
            
            # Basic quality check (not too dark, not too bright)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            
            if 20 < mean_brightness < 235:  # Skip very dark or very bright frames
                time_ms = int((frame_idx / fps) * 1000)
                time_s = time_ms / 1000.0
                
                # Save frame
                frame_filename = f"{video_name}_frame_{time_ms:08d}ms_{pass_name}.jpg"
                frame_path = str(output_dir / frame_filename)
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                candidate = FrameCandidate(
                    frame_idx=frame_idx,
                    time_ms=time_ms,
                    time_s=time_s,
                    frame=None,  # Don't keep in memory
                    frame_path=frame_path,
                    motion_score=motion_score,
                    stability_score=1.0 - min(motion_score, 1.0)
                )
                candidates.append(candidate)
            
            # Skip to next sample point
            frame_idx += interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        
        return candidates
    
    def _scene_change_pass(self, cap: cv2.VideoCapture, video_name: str, 
                           output_dir: Path, threshold: float = 0.3, 
                           pass_name: str = "scene") -> List[FrameCandidate]:
        """
        # シーンチェンジ検出パス（閾値0.3）
        Detect scene changes based on frame differences.
        """
        candidates = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, prev_frame = cap.read()
        if not ret:
            return candidates
            
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        frame_idx = 1
        
        while frame_idx < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # フレーム差分計算
            diff = cv2.absdiff(gray, prev_gray)
            diff_ratio = np.sum(diff > 30) / (gray.shape[0] * gray.shape[1])
            
            # シーンチェンジ検出
            if diff_ratio > threshold:
                time_ms = int((frame_idx / fps) * 1000)
                time_s = time_ms / 1000.0
                
                frame_filename = f"{video_name}_frame_{time_ms:08d}ms_{pass_name}.jpg"
                frame_path = str(output_dir / frame_filename)
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                candidates.append(FrameCandidate(
                    frame_idx=frame_idx,
                    time_ms=time_ms,
                    time_s=time_s,
                    frame=None,
                    frame_path=frame_path,
                    motion_score=diff_ratio
                ))
            
            prev_gray = gray
            frame_idx += max(1, int(fps * 0.1))  # 0.1秒ごとにチェック
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        
        return candidates
    
    def _motion_based_pass(self, cap: cv2.VideoCapture, video_name: str,
                           output_dir: Path, pass_name: str = "motion") -> List[FrameCandidate]:
        """
        # モーションベースサンプリング（大きな動きがある箇所）
        Sample frames with significant motion.
        """
        candidates = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # オプティカルフロー用の初期化
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, prev_frame = cap.read()
        if not ret:
            return candidates
            
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        frame_idx = int(fps * 0.5)  # 0.5秒から開始
        
        while frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # オプティカルフロー計算（簡易版）
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            
            # フロー大きさの平均
            magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
            avg_motion = np.mean(magnitude)
            
            # 大きな動きがある場合
            if avg_motion > 2.0 and avg_motion < 10.0:  # 適度な動き
                time_ms = int((frame_idx / fps) * 1000)
                time_s = time_ms / 1000.0
                
                frame_filename = f"{video_name}_frame_{time_ms:08d}ms_{pass_name}.jpg"
                frame_path = str(output_dir / frame_filename)
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                candidates.append(FrameCandidate(
                    frame_idx=frame_idx,
                    time_ms=time_ms,
                    time_s=time_s,
                    frame=None,
                    frame_path=frame_path,
                    motion_score=1.0 / (1.0 + avg_motion)  # 動きが少ないほど高スコア
                ))
                
                frame_idx += int(fps * 0.5)  # 次は0.5秒後
            else:
                frame_idx += int(fps * 0.2)  # 0.2秒後に再チェック
            
            prev_gray = gray
        
        return candidates
    
    def _calculate_motion(self, frame: np.ndarray) -> float:
        """
        Calculate motion/instability score using frame difference.
        
        Returns:
            Motion score 0-1 (0=stable, 1=high motion)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            return 0.0
        
        # Frame difference
        diff = cv2.absdiff(gray, self.prev_gray)
        motion_pixels = np.sum(diff > 30)  # Threshold for motion
        total_pixels = gray.shape[0] * gray.shape[1]
        motion_ratio = motion_pixels / total_pixels
        
        # Optional: Optical flow for more accurate motion detection
        if self.config.debug:
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray, None,
                pyr_scale=0.5, levels=1, winsize=15,
                iterations=1, poly_n=5, poly_sigma=1.1, flags=0
            )
            magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
            motion_magnitude = np.mean(magnitude)
            motion_score = min(motion_magnitude / 10.0, 1.0)
        else:
            motion_score = min(motion_ratio * 5, 1.0)
        
        self.prev_gray = gray
        return motion_score