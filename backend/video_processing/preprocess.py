"""
Image preprocessing and perspective correction for receipts.
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple
from pathlib import Path
from .types import DocumentQuad, Config

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Preprocess and enhance document images for OCR.
    """
    
    def __init__(self, config: Config):
        self.config = config
        
    def process_frame(self, image_path: str, doc_quad: Optional[DocumentQuad],
                     output_path: str) -> bool:
        """
        Process a frame with perspective correction and enhancement.
        
        Args:
            image_path: Path to input image
            doc_quad: Detected document quadrilateral
            output_path: Path to save processed image
            
        Returns:
            True if successful
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to load image: {image_path}")
                return False
            
            # Apply perspective correction if document detected (unless skipped)
            if doc_quad and doc_quad.points is not None and not self.config.skip_perspective_correction:
                corrected = self._perspective_correct(image, doc_quad.points)
            else:
                corrected = image
            
            # Auto-rotate if needed (currently disabled to avoid issues)
            # rotated = self._auto_rotate(corrected)
            rotated = corrected  # 一時的に回転処理をスキップ
            
            # Enhance for OCR (skip if configured)
            if self.config.skip_enhancement:
                enhanced = rotated  # 画像処理をスキップして原画像を使用
            else:
                enhanced = self._enhance_for_ocr(rotated)
            
            # Save with high quality JPEG (95% quality)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(output_path, enhanced, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            return True
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return False
    
    def _perspective_correct(self, image: np.ndarray, 
                            corners: np.ndarray) -> np.ndarray:
        """
        Apply perspective transformation to rectify document.
        """
        # Get dimensions
        rect = self._order_points(corners)
        (tl, tr, br, bl) = rect
        
        # Compute width and height of destination
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))
        
        # Add padding
        padding = self.config.warp_padding_percent
        maxWidth = int(maxWidth * (1 + 2 * padding))
        maxHeight = int(maxHeight * (1 + 2 * padding))
        
        # Destination points
        dst = np.array([
            [maxWidth * padding, maxHeight * padding],
            [maxWidth * (1 - padding), maxHeight * padding],
            [maxWidth * (1 - padding), maxHeight * (1 - padding)],
            [maxWidth * padding, maxHeight * (1 - padding)]
        ], dtype="float32")
        
        # Perspective transform with white background
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight), 
                                     borderMode=cv2.BORDER_CONSTANT,
                                     borderValue=(255, 255, 255))  # 白い背景色
        
        return warped
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """
        Order points as: top-left, top-right, bottom-right, bottom-left.
        """
        rect = np.zeros((4, 2), dtype="float32")
        
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def _auto_rotate(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and correct image rotation using Hough lines.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
        
        if lines is not None and len(lines) > 0:
            # Extract angles
            angles = []
            for line in lines[:20]:  # Use top 20 lines
                rho, theta = line[0]
                angle_deg = theta * 180 / np.pi - 90
                
                # Keep angles close to horizontal/vertical
                if abs(angle_deg) < 45:
                    angles.append(angle_deg)
            
            if angles:
                # Median angle
                median_angle = np.median(angles)
                
                # Only rotate if angle is significant
                if abs(median_angle) > 1.0:
                    logger.debug(f"Auto-rotating by {median_angle:.1f} degrees")
                    return self._rotate_image(image, median_angle)
        
        return image
    
    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotate image by given angle.
        """
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        # Rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Calculate new dimensions
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # Adjust rotation matrix for translation
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        # Perform rotation
        rotated = cv2.warpAffine(image, M, (new_w, new_h), 
                                flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT,
                                borderValue=(255, 255, 255))
        
        return rotated
    
    def _enhance_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """
        # OCR精度向上のための画像処理
        Enhanced image processing for better OCR accuracy.
        """
        # グレースケールに変換
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 1. デノイジング（ノイズ除去）
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # 2. コントラスト調整 (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 3. シャープニング
        kernel = np.array([[-1,-1,-1],
                           [-1, 9,-1],
                           [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # 4. 適応的二値化（テキスト強調）
        binary = cv2.adaptiveThreshold(sharpened, 255,
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 11, 2)
        
        # 5. モルフォロジー処理（文字の連結性向上）
        kernel = np.ones((2,2), np.uint8)
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # BGRに戻す（Vision APIはカラー画像を期待）
        result = cv2.cvtColor(morph, cv2.COLOR_GRAY2BGR)
        
        return result
    
    def _assess_binary_quality(self, binary: np.ndarray) -> float:
        """
        Assess if binary image is suitable for OCR.
        """
        # Check if not too much is lost
        white_ratio = np.sum(binary == 255) / binary.size
        
        # Good range: 60-90% white
        if 0.6 < white_ratio < 0.9:
            return 1.0
        elif 0.5 < white_ratio < 0.95:
            return 0.5
        else:
            return 0.0