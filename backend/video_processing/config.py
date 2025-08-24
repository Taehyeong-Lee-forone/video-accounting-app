"""
Configuration management for video processing.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
from .types import Config

logger = logging.getLogger(__name__)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from file or use defaults.
    
    Args:
        config_path: Optional path to JSON config file
        
    Returns:
        Config object with loaded or default values
    """
    config = Config()
    
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
                for key, value in config_dict.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            logger.info(f"Loaded config from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    # Environment variable overrides
    if os.getenv("VP_DEBUG"):
        config.debug = os.getenv("VP_DEBUG").lower() == "true"
    if os.getenv("VP_TARGET_MIN"):
        config.target_min = int(os.getenv("VP_TARGET_MIN"))
    if os.getenv("VP_TARGET_MAX"):
        config.target_max = int(os.getenv("VP_TARGET_MAX"))
    
    # Validate weights sum to 1.0 (excluding penalty)
    positive_weights = (
        config.weight_sharpness +
        config.weight_doc_area +
        config.weight_perspective +
        config.weight_exposure +
        config.weight_stability +
        config.weight_textness
    )
    
    if abs(positive_weights - 1.0) > 0.01:
        logger.warning(f"Quality weights sum to {positive_weights}, normalizing...")
        # Normalize weights
        config.weight_sharpness /= positive_weights
        config.weight_doc_area /= positive_weights
        config.weight_perspective /= positive_weights
        config.weight_exposure /= positive_weights
        config.weight_stability /= positive_weights
        config.weight_textness /= positive_weights
    
    return config


def save_config(config: Config, config_path: str) -> None:
    """Save configuration to JSON file."""
    config_dict = {
        key: value for key, value in config.__dict__.items()
        if not key.startswith('_')
    }
    
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=2, default=str)
    
    logger.info(f"Saved config to {config_path}")