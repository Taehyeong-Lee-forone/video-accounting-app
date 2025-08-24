"""
Document detection and perspective analysis for receipt frames.
"""

import cv2
import numpy as np
import logging
from typing import Optional, List, Tuple
from .types import DocumentQuad, Config

logger = logging.getLogger(__name__)


class DocumentDetector:
    """
    Detect document boundaries and evaluate perspective quality.
    """
    
    def __init__(self, config: Config):
        self.config = config
        
    def detect_document(self, image: np.ndarray) -> Optional[DocumentQuad]:
        """
        Detect the largest rectangular document in the image.
        
        Args:
            image: Input image (BGR)
            
        Returns:
            DocumentQuad with corner points and quality metrics
        """
        height, width = image.shape[:2]
        frame_area = height * width
        
        # Preprocess
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Edge detection with multiple scales
        edges = self._multi_scale_edge_detection(gray)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Sort by area
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Find best document candidate
        for contour in contours[:10]:  # Check top 10 largest contours
            area = cv2.contourArea(contour)
            area_ratio = area / frame_area
            
            # Skip if too small
            if area_ratio < self.config.min_doc_area_ratio:
                continue
            
            # Approximate to polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # Look for quadrilateral
            if len(approx) == 4:
                quad = self._order_points(approx.reshape(4, 2))
                
                # Check if it's rectangular enough
                rectangularity = self._calculate_rectangularity(quad)
                if rectangularity < 0.7:  # Not rectangular enough
                    continue
                
                # Check aspect ratio
                aspect_ratio = self._calculate_aspect_ratio(quad)
                min_ar, max_ar = self.config.doc_aspect_ratio_range
                if not (min_ar <= aspect_ratio <= max_ar):
                    continue
                
                # Calculate perspective score
                perspective_score = self._calculate_perspective_score(quad, width, height)
                
                return DocumentQuad(
                    points=quad,
                    confidence=rectangularity,
                    area_ratio=area_ratio,
                    rectangularity=rectangularity,
                    perspective_score=perspective_score
                )
        
        return None
    
    def _multi_scale_edge_detection(self, gray: np.ndarray) -> np.ndarray:
        """
        Detect edges at multiple scales for robustness.
        """
        # Apply bilateral filter to reduce noise while keeping edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(filtered)
        
        # Multi-scale Canny
        edges1 = cv2.Canny(enhanced, 50, 150)
        edges2 = cv2.Canny(enhanced, 100, 200)
        
        # Morphological operations to connect edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.bitwise_or(edges1, edges2)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        return edges
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """
        Order points as: top-left, top-right, bottom-right, bottom-left.
        """
        rect = np.zeros((4, 2), dtype=np.float32)
        
        # Sum and diff for corner detection
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        
        rect[0] = pts[np.argmin(s)]     # Top-left
        rect[2] = pts[np.argmax(s)]     # Bottom-right
        rect[1] = pts[np.argmin(diff)]  # Top-right
        rect[3] = pts[np.argmax(diff)]  # Bottom-left
        
        return rect
    
    def _calculate_rectangularity(self, quad: np.ndarray) -> float:
        """
        Calculate how rectangular the quadrilateral is (0-1).
        """
        # Calculate angles at each corner
        angles = []
        for i in range(4):
            p1 = quad[i]
            p2 = quad[(i + 1) % 4]
            p3 = quad[(i - 1) % 4]
            
            v1 = p1 - p3
            v2 = p2 - p1
            
            angle = np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6))
            angles.append(abs(angle - np.pi/2))
        
        # Lower deviation from 90 degrees = more rectangular
        avg_deviation = np.mean(angles)
        rectangularity = 1.0 - min(avg_deviation / (np.pi/4), 1.0)
        
        return rectangularity
    
    def _calculate_aspect_ratio(self, quad: np.ndarray) -> float:
        """
        Calculate aspect ratio of the quadrilateral.
        """
        # Calculate width and height
        width = max(
            np.linalg.norm(quad[1] - quad[0]),
            np.linalg.norm(quad[2] - quad[3])
        )
        height = max(
            np.linalg.norm(quad[3] - quad[0]),
            np.linalg.norm(quad[2] - quad[1])
        )
        
        return width / (height + 1e-6)
    
    def _calculate_perspective_score(self, quad: np.ndarray, 
                                    img_width: int, img_height: int) -> float:
        """
        Calculate perspective distortion score (0-1, higher is better).
        """
        # Check if quad is mostly upright and not too skewed
        top_width = np.linalg.norm(quad[1] - quad[0])
        bottom_width = np.linalg.norm(quad[2] - quad[3])
        left_height = np.linalg.norm(quad[3] - quad[0])
        right_height = np.linalg.norm(quad[2] - quad[1])
        
        # Width and height consistency
        width_ratio = min(top_width, bottom_width) / max(top_width, bottom_width)
        height_ratio = min(left_height, right_height) / max(left_height, right_height)
        
        # Check if corners are not too close to image edges
        margin = 0.02  # 2% margin
        margins_ok = all([
            np.all(quad[:, 0] > img_width * margin),
            np.all(quad[:, 0] < img_width * (1 - margin)),
            np.all(quad[:, 1] > img_height * margin),
            np.all(quad[:, 1] < img_height * (1 - margin))
        ])
        
        margin_score = 1.0 if margins_ok else 0.8
        
        # Combined score
        perspective_score = (width_ratio * 0.4 + height_ratio * 0.4 + margin_score * 0.2)
        
        return perspective_score