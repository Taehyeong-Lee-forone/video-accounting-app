"""
Type definitions for the video processing package.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
import numpy as np


@dataclass
class Config:
    """Configuration for video processing pipeline."""
    
    # Sampling parameters
    base_fps: float = 4.0
    offset_fps: float = 4.0
    offset_shift: float = 0.125  # 125ms shift for offset sampling
    
    # Quality weights (positive weights must sum to 1.0)
    weight_sharpness: float = 0.20
    weight_doc_area: float = 0.25
    weight_perspective: float = 0.15
    weight_exposure: float = 0.10
    weight_stability: float = 0.15  # Increased from 0.10
    weight_glare_penalty: float = -0.10  # Penalty (negative)
    weight_textness: float = 0.15  # Reduced from 35%
    
    # NMS parameters
    temporal_window: float = 0.6  # seconds
    temporal_window_relaxed: float = 0.4  # fallback
    visual_eps: int = 8  # hamming distance for pHash
    visual_eps_relaxed: int = 9  # fallback
    
    # Document detection
    min_doc_area_ratio: float = 0.12  # min 12% of frame
    max_glare_ratio: float = 0.07  # max 7% saturated pixels
    doc_aspect_ratio_range: Tuple[float, float] = (0.4, 2.5)  # typical receipt ratios
    
    # Target frame counts
    target_min: int = 7
    target_max: int = 15
    
    # Text deduplication
    text_jaccard_threshold: float = 0.85
    text_token_similarity: float = 0.90
    
    # Processing parameters
    warp_padding_percent: float = 0.03  # 3% padding
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    skip_enhancement: bool = False  # Enable image enhancement for better OCR accuracy
    skip_perspective_correction: bool = False  # Enable perspective correction for better document alignment
    
    # Debug/logging
    debug: bool = False
    save_intermediate: bool = False


@dataclass
class DocumentQuad:
    """Represents a detected document as 4 corner points."""
    points: np.ndarray  # shape (4, 2) - TL, TR, BR, BL
    confidence: float = 1.0
    area_ratio: float = 0.0
    rectangularity: float = 0.0
    perspective_score: float = 0.0


@dataclass
class FrameCandidate:
    """A candidate frame with quality metrics."""
    frame_idx: int
    time_ms: int
    time_s: float
    frame: Optional[np.ndarray]  # Can be None after processing
    frame_path: str
    
    # Quality scores
    sharpness_score: float = 0.0
    doc_area_score: float = 0.0
    perspective_score: float = 0.0
    exposure_score: float = 0.0
    stability_score: float = 0.0
    glare_penalty: float = 0.0
    textness_score: float = 0.0
    total_score: float = 0.0
    
    # Document detection
    doc_quad: Optional[DocumentQuad] = None
    has_document: bool = False
    
    # Visual fingerprint
    phash: Optional[str] = None
    dhash: Optional[str] = None
    
    # Motion/stability
    motion_score: float = 0.0
    optical_flow_magnitude: float = 0.0


@dataclass
class SelectedFrame:
    """Final selected frame with all processing results."""
    time_s: float
    score: float
    doc_quad: Optional[List[List[float]]]  # [[x,y], [x,y], [x,y], [x,y]]
    crop_path: str  # Path to perspective-corrected and enhanced image
    phash: str
    ocr_text: Optional[str] = None
    ocr_conf: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "time_s": self.time_s,
            "score": self.score,
            "doc_quad": self.doc_quad,
            "crop_path": self.crop_path,
            "phash": self.phash,
            "ocr_text": self.ocr_text,
            "ocr_conf": self.ocr_conf,
            "metadata": self.metadata
        }


@dataclass
class TextBlock:
    """Detected text block from OCR."""
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    tokens: Optional[List[str]] = None
    ngrams: Optional[set] = None