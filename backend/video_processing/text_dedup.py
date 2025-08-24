"""
Text deduplication for OCR results.
"""

import logging
from typing import List, Dict, Any, Set, Tuple, Optional
import hashlib
from .types import TextBlock, Config

logger = logging.getLogger(__name__)


class TextDeduplicator:
    """
    Remove duplicate text content from OCR results.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.seen_hashes = set()
        self.seen_keys = set()
        
    def deduplicate(self, text_blocks: List[Tuple[Any, TextBlock]]) -> List[Tuple[Any, TextBlock]]:
        """
        Remove duplicate text blocks based on similarity.
        
        Args:
            text_blocks: List of (frame, text_block) tuples
            
        Returns:
            Deduplicated list
        """
        if not text_blocks:
            return []
        
        # Sort by confidence (keep higher confidence)
        text_blocks = sorted(text_blocks, 
                            key=lambda x: x[1].confidence if x[1] else 0, 
                            reverse=True)
        
        deduplicated = []
        
        for frame, text_block in text_blocks:
            if not text_block or not text_block.text:
                continue
            
            # Check for duplicates
            if self._is_duplicate(text_block):
                logger.debug(f"Skipping duplicate text at {frame.time_s}s")
                continue
            
            # Add to seen
            self._add_to_seen(text_block)
            deduplicated.append((frame, text_block))
        
        return deduplicated
    
    def _is_duplicate(self, text_block: TextBlock) -> bool:
        """
        Check if text block is duplicate of previously seen text.
        """
        # Exact hash check
        text_hash = hashlib.md5(text_block.text.encode()).hexdigest()
        if text_hash in self.seen_hashes:
            return True
        
        # N-gram similarity check
        if text_block.ngrams:
            for seen_ngrams in self.seen_keys:
                similarity = self._jaccard_similarity(
                    text_block.ngrams, 
                    seen_ngrams
                )
                if similarity >= self.config.text_jaccard_threshold:
                    return True
        
        # Token similarity check
        if text_block.tokens:
            for seen_tokens in self.seen_keys:
                if isinstance(seen_tokens, list):
                    similarity = self._token_similarity(
                        text_block.tokens,
                        seen_tokens
                    )
                    if similarity >= self.config.text_token_similarity:
                        return True
        
        return False
    
    def _add_to_seen(self, text_block: TextBlock):
        """
        Add text block to seen collections.
        """
        # Add hash
        text_hash = hashlib.md5(text_block.text.encode()).hexdigest()
        self.seen_hashes.add(text_hash)
        
        # Add ngrams
        if text_block.ngrams:
            # Store as frozen set for hashability
            self.seen_keys.add(frozenset(text_block.ngrams))
        
        # Add tokens
        if text_block.tokens:
            self.seen_keys.add(tuple(text_block.tokens))
    
    def _jaccard_similarity(self, set1: set, set2: Any) -> float:
        """
        Calculate Jaccard similarity between two sets.
        """
        if isinstance(set2, frozenset):
            set2 = set(set2)
        elif not isinstance(set2, set):
            return 0.0
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _token_similarity(self, tokens1: List[str], tokens2: Any) -> float:
        """
        Calculate token-based similarity.
        """
        if isinstance(tokens2, tuple):
            tokens2 = list(tokens2)
        elif not isinstance(tokens2, list):
            return 0.0
        
        if not tokens1 or not tokens2:
            return 0.0
        
        set1 = set(tokens1)
        set2 = set(tokens2)
        
        intersection = len(set1 & set2)
        smaller_set = min(len(set1), len(set2))
        
        return intersection / smaller_set if smaller_set > 0 else 0.0
    
    def create_session_key(self, receipt_info: Dict[str, Any]) -> Optional[str]:
        """
        Create a unique key for receipt based on date and amount.
        """
        if not receipt_info:
            return None
        
        date = receipt_info.get('date', '')
        total = receipt_info.get('total', 0)
        
        if not date and not total:
            return None
        
        # Create composite key
        key_parts = []
        
        if date:
            key_parts.append(f"d:{date}")
        if total:
            key_parts.append(f"t:{int(total)}")
        
        key = '|'.join(key_parts)
        
        # Hash for compactness
        return hashlib.md5(key.encode()).hexdigest()[:16]