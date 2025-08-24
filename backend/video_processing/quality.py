"""
Frame quality assessment for receipt detection.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Dict, Any, Optional
from .types import FrameCandidate, DocumentQuad, Config

logger = logging.getLogger(__name__)


class QualityAssessor:
    """
    Comprehensive quality assessment for receipt frames.
    """
    
    def __init__(self, config: Config):
        self.config = config
        
    def assess_frame(self, frame: np.ndarray, 
                    doc_quad: Optional[DocumentQuad] = None,
                    motion_score: float = 0.0) -> Dict[str, float]:
        """
        Calculate comprehensive quality scores for a frame.
        
        Args:
            frame: Input image (BGR)
            doc_quad: Detected document quadrilateral
            motion_score: Motion/instability score from sampling
            
        Returns:
            Dictionary of quality scores
        """
        scores = {}
        
        # Sharpness (Laplacian variance)
        scores['sharpness'] = self._calculate_sharpness(frame)
        
        # Document area score
        if doc_quad:
            scores['doc_area'] = doc_quad.area_ratio / 0.5  # Normalize to 0-1 (50% = 1.0)
            scores['doc_area'] = min(scores['doc_area'], 1.0)
            scores['perspective'] = doc_quad.perspective_score
        else:
            scores['doc_area'] = 0.0
            scores['perspective'] = 0.0
        
        # Exposure and contrast
        scores['exposure'], scores['contrast'] = self._calculate_exposure_contrast(frame)
        
        # Motion/stability (inverse of motion)
        scores['stability'] = 1.0 - min(motion_score, 1.0)
        
        # Glare detection (negative score)
        scores['glare_penalty'] = -self._detect_glare(frame)
        
        # Text density (simplified)
        scores['textness'] = self._estimate_text_density(frame, doc_quad)
        
        # Calculate weighted total
        total = (
            scores['sharpness'] * self.config.weight_sharpness +
            scores['doc_area'] * self.config.weight_doc_area +
            scores['perspective'] * self.config.weight_perspective +
            scores['exposure'] * self.config.weight_exposure +
            scores['stability'] * self.config.weight_stability +
            scores['glare_penalty'] * abs(self.config.weight_glare_penalty) +
            scores['textness'] * self.config.weight_textness
        )
        
        scores['total'] = max(0.0, min(1.0, total))
        
        return scores
    
    def _calculate_sharpness(self, image: np.ndarray) -> float:
        """
        Calculate sharpness using Laplacian variance.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        # Normalize using log scale (typical range 0-5000)
        sharpness = np.log(variance + 1) / np.log(5000)
        return min(1.0, sharpness)
    
    def _calculate_exposure_contrast(self, image: np.ndarray) -> Tuple[float, float]:
        """
        Calculate exposure quality and contrast.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Exposure: Check if histogram is well-distributed
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()
        
        # Check for clipping
        low_clip = hist[:10].sum()
        high_clip = hist[-10:].sum()
        clipping_penalty = (low_clip + high_clip) * 2
        
        # Entropy as measure of information content
        entropy = -np.sum(hist * np.log2(hist + 1e-10))
        entropy_norm = entropy / 8.0  # Normalize (max ~8 for uniform)
        
        exposure_score = max(0, 1.0 - clipping_penalty)
        contrast_score = min(1.0, entropy_norm)
        
        return exposure_score, contrast_score
    
    def _detect_glare(self, image: np.ndarray) -> float:
        """
        Detect glare/specular highlights.
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect high value (brightness) with low saturation
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        
        # Glare pixels: very bright and low saturation
        glare_mask = (value > 250) & (saturation < 30)
        glare_ratio = np.sum(glare_mask) / glare_mask.size
        
        # Also check for pure white areas in RGB
        white_mask = np.all(image > 250, axis=2)
        white_ratio = np.sum(white_mask) / white_mask.size
        
        total_glare = max(glare_ratio, white_ratio)
        
        # Penalty increases sharply above threshold
        if total_glare > self.config.max_glare_ratio:
            return min(1.0, total_glare * 3)
        return total_glare
    
    def _estimate_text_density(self, image: np.ndarray, 
                               doc_quad: Optional[DocumentQuad] = None) -> float:
        """
        Estimate text density using edge detection and morphology.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # If document detected, crop to document area
        if doc_quad and doc_quad.points is not None:
            # Create mask for document area
            mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.fillPoly(mask, [doc_quad.points.astype(int)], 255)
            gray = cv2.bitwise_and(gray, mask)
        
        # Enhance for text detection
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Edge detection optimized for text
        edges = cv2.Canny(enhanced, 50, 150)
        
        # Morphological operations to connect text regions
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        
        text_regions = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_h)
        text_regions = cv2.morphologyEx(text_regions, cv2.MORPH_CLOSE, kernel_v)
        
        # Count text-like regions
        contours, _ = cv2.findContours(text_regions, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size and aspect ratio (text-like)
        text_contours = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = w / (h + 1e-6)
            area = cv2.contourArea(cnt)
            
            # Text-like: horizontal, reasonable size
            if 0.5 < aspect_ratio < 20 and area > 20:
                text_contours.append(cnt)
        
        # Calculate density
        if doc_quad:
            doc_area = doc_quad.area_ratio * gray.shape[0] * gray.shape[1]
        else:
            doc_area = gray.shape[0] * gray.shape[1]
        
        text_area = sum(cv2.contourArea(cnt) for cnt in text_contours)
        text_density = text_area / (doc_area + 1e-6)
        
        # Normalize (typical range 0-0.3)
        normalized_density = min(1.0, text_density * 3.33)
        
        # Also consider number of text regions
        region_score = min(1.0, len(text_contours) / 50.0)
        
        # Combined score
        return normalized_density * 0.7 + region_score * 0.3