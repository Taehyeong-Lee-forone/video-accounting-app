"""
Video Processing Package for High-Quality Receipt Frame Selection

This package implements an advanced frame selection system for extracting
the best quality receipt images from video with minimal duplicates.
"""

from .extract_best_frames import select_receipt_frames
from .types import SelectedFrame, Config

__version__ = "1.0.0"
__all__ = ["select_receipt_frames", "SelectedFrame", "Config"]