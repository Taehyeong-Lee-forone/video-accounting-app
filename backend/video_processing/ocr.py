"""
OCR processing using Google Cloud Vision API.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from google.cloud import vision
from google.api_core import exceptions
from .types import TextBlock, Config

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    OCR processing with Google Cloud Vision API.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize Vision API client."""
        try:
            self.client = vision.ImageAnnotatorClient()
            logger.info("Vision API client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Vision API client: {e}")
            self.client = None
    
    def process_image(self, image_path: str) -> Optional[TextBlock]:
        """
        Perform OCR on an image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            TextBlock with extracted text and confidence
        """
        if not self.client:
            logger.error("Vision API client not initialized")
            return None
        
        try:
            # Load image
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            
            # Perform OCR with language hints
            response = self.client.document_text_detection(
                image=image,
                image_context={'language_hints': ['ja', 'en', 'ko']}
            )
            
            if response.error.message:
                logger.error(f"Vision API error: {response.error.message}")
                return None
            
            # Extract text and confidence
            if response.full_text_annotation:
                text = response.full_text_annotation.text
                
                # Calculate average confidence
                confidences = []
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        if block.confidence:
                            confidences.append(block.confidence)
                
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                # Extract tokens for similarity comparison
                tokens = self._extract_tokens(text)
                ngrams = self._generate_ngrams(tokens, n=3)
                
                return TextBlock(
                    text=text,
                    confidence=avg_confidence,
                    tokens=tokens,
                    ngrams=ngrams
                )
            
            return None
            
        except Exception as e:
            logger.error(f"OCR processing failed for {image_path}: {e}")
            return None
    
    def _extract_tokens(self, text: str) -> List[str]:
        """
        Extract normalized tokens from text.
        """
        import re
        
        # Basic tokenization
        text = text.lower()
        
        # Remove special characters but keep numbers
        text = re.sub(r'[^\w\s\d]', ' ', text)
        
        # Split and filter
        tokens = text.split()
        tokens = [t for t in tokens if len(t) > 1]
        
        return tokens
    
    def _generate_ngrams(self, tokens: List[str], n: int = 3) -> set:
        """
        Generate n-grams from tokens.
        """
        if len(tokens) < n:
            return set(tokens)
        
        ngrams = set()
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i+n])
            ngrams.add(ngram)
        
        return ngrams
    
    def extract_receipt_info(self, text: str) -> Dict[str, Any]:
        """
        Extract structured receipt information from OCR text.
        Uses VisionOCRService for better extraction accuracy.
        """
        try:
            # Use the existing VisionOCRService for better extraction
            from services.vision_ocr import VisionOCRService
            vision_service = VisionOCRService()
            
            # Parse using the more sophisticated logic
            receipt_data = vision_service.parse_receipt_data({'full_text': text})
            
            # Map to our format
            info = {
                'vendor': receipt_data.get('vendor'),
                'total': receipt_data.get('total'),
                'subtotal': receipt_data.get('subtotal'),
                'tax': receipt_data.get('tax'),
                'tax_rate': receipt_data.get('tax_rate'),
                'date': receipt_data.get('issue_date'),
                'payment_method': receipt_data.get('payment_method'),
                'document_type': receipt_data.get('document_type'),
                'currency': 'JPY'  # Default to JPY
            }
            
            return info
            
        except Exception as e:
            logger.warning(f"Failed to use VisionOCRService, falling back to simple extraction: {e}")
            
            # Fallback to simple extraction
            import re
            
            info = {
                'date': None,
                'total': None,
                'currency': 'JPY',
                'vendor': None
            }
            
            # Simple vendor extraction - first non-empty line
            lines = text.split('\n')
            for line in lines[:5]:
                line = line.strip()
                if len(line) > 3:
                    info['vendor'] = line
                    break
            
            # Simple total extraction
            total_patterns = [
                r'合計[：:\s]*([¥￥]?[\d,]+)円?',
                r'総額[：:\s]*([¥￥]?[\d,]+)円?',
                r'お支払[：:\s]*([¥￥]?[\d,]+)円?'
            ]
            
            for pattern in total_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1)
                    amount_str = re.sub(r'[¥￥,円]', '', amount_str)
                    try:
                        info['total'] = float(amount_str)
                        break
                    except:
                        pass
            
            return info