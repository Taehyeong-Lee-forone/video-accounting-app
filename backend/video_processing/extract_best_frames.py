"""
Main entry point for high-quality receipt frame extraction.
"""

import cv2
import json
import logging
import time
from pathlib import Path
from typing import List, Optional
import argparse
import sys

from .types import Config, SelectedFrame, FrameCandidate
from .config import load_config
from .sampling import AdaptiveSampler
from .doc_detect import DocumentDetector
from .quality import QualityAssessor
from .nms import NMSProcessor
from .preprocess import ImagePreprocessor
from .ocr import OCRProcessor
from .text_dedup import TextDeduplicator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def select_receipt_frames(
    video_path: str,
    target_min: int = 7,
    target_max: int = 15,
    config: Optional[Config] = None
) -> List[SelectedFrame]:
    """
    Extract best quality receipt frames from video.
    
    This is the main API for the video processing package.
    
    Args:
        video_path: Path to input video file
        target_min: Minimum number of frames to select
        target_max: Maximum number of frames to select
        config: Optional configuration object
        
    Returns:
        List of SelectedFrame objects with processed receipt images
        
    Example:
        >>> frames = select_receipt_frames("video.mp4", target_min=5, target_max=10)
        >>> for frame in frames:
        ...     print(f"Time: {frame.time_s}s, Score: {frame.score:.2f}")
        ...     print(f"OCR Text: {frame.ocr_text[:100]}...")
    """
    start_time = time.time()
    
    # Load configuration
    if config is None:
        config = load_config()
    
    # Override targets if specified
    config.target_min = target_min
    config.target_max = target_max
    
    logger.info(f"Processing video: {video_path}")
    logger.info(f"Target frames: {target_min}-{target_max}")
    
    # Create output directories
    output_dir = Path("output")
    crops_dir = output_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Adaptive sampling
    logger.info("Step 1: Adaptive frame sampling...")
    sampler = AdaptiveSampler(config)
    candidates = sampler.sample_frames(video_path)
    logger.info(f"Sampled {len(candidates)} candidate frames")
    
    # Step 2: Document detection and quality assessment
    logger.info("Step 2: Document detection and quality scoring...")
    detector = DocumentDetector(config)
    assessor = QualityAssessor(config)
    
    scored_candidates = []
    for i, candidate in enumerate(candidates):
        if i % 10 == 0:
            logger.debug(f"Processing frame {i+1}/{len(candidates)}")
        
        # Load frame
        frame = cv2.imread(candidate.frame_path)
        if frame is None:
            continue
        
        # Detect document
        doc_quad = detector.detect_document(frame)
        candidate.doc_quad = doc_quad
        candidate.has_document = doc_quad is not None
        
        # Assess quality
        scores = assessor.assess_frame(
            frame, 
            doc_quad, 
            candidate.motion_score
        )
        
        # Update candidate with scores
        candidate.sharpness_score = scores['sharpness']
        candidate.doc_area_score = scores['doc_area']
        candidate.perspective_score = scores['perspective']
        candidate.exposure_score = scores['exposure']
        candidate.stability_score = scores['stability']
        candidate.glare_penalty = scores['glare_penalty']
        candidate.textness_score = scores['textness']
        candidate.total_score = scores['total']
        
        # Only keep frames with reasonable scores
        if candidate.total_score > 0.1:
            scored_candidates.append(candidate)
    
    logger.info(f"Scored {len(scored_candidates)} frames above threshold")
    
    # Step 3: Non-Maximum Suppression
    logger.info("Step 3: Applying NMS for frame selection...")
    nms = NMSProcessor(config)
    selected_candidates = nms.apply_adaptive_selection(scored_candidates)
    logger.info(f"Selected {len(selected_candidates)} frames after NMS")
    
    # Step 4: Preprocessing and OCR
    logger.info("Step 4: Preprocessing and OCR...")
    preprocessor = ImagePreprocessor(config)
    ocr_processor = OCRProcessor(config)
    
    ocr_results = []
    for i, candidate in enumerate(selected_candidates):
        logger.debug(f"Processing selected frame {i+1}/{len(selected_candidates)}")
        
        # Generate output path
        video_name = Path(video_path).stem
        crop_filename = f"{video_name}_crop_{int(candidate.time_s*1000):08d}ms.jpg"
        crop_path = str(crops_dir / crop_filename)
        
        # ビデオから直接フレームを抽出
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, candidate.time_s * 1000)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            logger.warning(f"Failed to extract frame at {candidate.time_s}s")
            success = False
        else:
            # フレームを一時的に保存
            temp_frame_path = f"/tmp/temp_frame_{int(candidate.time_s*1000)}.jpg"
            cv2.imwrite(temp_frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Preprocess
            success = preprocessor.process_frame(
                temp_frame_path,
                candidate.doc_quad,
                crop_path
            )
            
            # 一時ファイルを削除
            import os
            if os.path.exists(temp_frame_path):
                os.remove(temp_frame_path)
        
        if success:
            # OCR
            text_block = ocr_processor.process_image(crop_path)
            
            if text_block:
                # Extract receipt info
                receipt_info = ocr_processor.extract_receipt_info(text_block.text)
                
                ocr_results.append((candidate, text_block, crop_path, receipt_info))
            else:
                ocr_results.append((candidate, None, crop_path, None))
        else:
            ocr_results.append((candidate, None, candidate.frame_path, None))
    
    # Step 5: Text deduplication
    logger.info("Step 5: Text deduplication...")
    deduplicator = TextDeduplicator(config)
    
    # Prepare for deduplication
    text_pairs = [(c, tb) for c, tb, _, _ in ocr_results if tb is not None]
    deduplicated = deduplicator.deduplicate(text_pairs)
    
    # Create final selected frames
    selected_frames = []
    deduplicated_times = set(c.time_s for c, _ in deduplicated)
    
    for candidate, text_block, crop_path, receipt_info in ocr_results:
        # Skip if deduplicated
        if text_block and candidate.time_s not in deduplicated_times:
            continue
        
        # Convert document quad to list format
        doc_quad_list = None
        if candidate.doc_quad and candidate.doc_quad.points is not None:
            doc_quad_list = candidate.doc_quad.points.tolist()
        
        selected_frame = SelectedFrame(
            time_s=candidate.time_s,
            score=candidate.total_score,
            doc_quad=doc_quad_list,
            crop_path=crop_path,
            phash=candidate.phash or "0"*16,
            ocr_text=text_block.text if text_block else None,
            ocr_conf=text_block.confidence if text_block else None,
            metadata={
                'scores': {
                    'sharpness': candidate.sharpness_score,
                    'doc_area': candidate.doc_area_score,
                    'perspective': candidate.perspective_score,
                    'exposure': candidate.exposure_score,
                    'stability': candidate.stability_score,
                    'textness': candidate.textness_score,
                    'glare_penalty': candidate.glare_penalty
                },
                'receipt_info': receipt_info
            }
        )
        selected_frames.append(selected_frame)
    
    # Sort by time
    selected_frames.sort(key=lambda x: x.time_s)
    
    elapsed = time.time() - start_time
    logger.info(f"Processing complete in {elapsed:.1f}s")
    logger.info(f"Final selection: {len(selected_frames)} frames")
    
    return selected_frames


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Extract high-quality receipt frames from video"
    )
    parser.add_argument(
        "--video", 
        required=True,
        help="Path to input video file"
    )
    parser.add_argument(
        "--out",
        default="output/frames.json",
        help="Output JSON file path"
    )
    parser.add_argument(
        "--save-crops",
        default="output/crops",
        help="Directory to save cropped images"
    )
    parser.add_argument(
        "--min-frames",
        type=int,
        default=7,
        help="Minimum number of frames to extract"
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=15,
        help="Maximum number of frames to extract"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration JSON file"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load config
    config = load_config(args.config) if args.config else None
    
    try:
        # Process video
        frames = select_receipt_frames(
            args.video,
            target_min=args.min_frames,
            target_max=args.max_frames,
            config=config
        )
        
        # Save results
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                [frame.to_dict() for frame in frames],
                f,
                indent=2,
                ensure_ascii=False
            )
        
        print(f"✓ Extracted {len(frames)} frames")
        print(f"✓ Results saved to {output_path}")
        print(f"✓ Cropped images saved to {args.save_crops}")
        
        # Print summary
        for i, frame in enumerate(frames, 1):
            print(f"\nFrame {i}:")
            print(f"  Time: {frame.time_s:.2f}s")
            print(f"  Score: {frame.score:.3f}")
            if frame.ocr_text:
                preview = frame.ocr_text[:50].replace('\n', ' ')
                print(f"  Text: {preview}...")
            if frame.metadata and frame.metadata.get('receipt_info'):
                info = frame.metadata['receipt_info']
                if info.get('vendor'):
                    print(f"  Vendor: {info['vendor']}")
                if info.get('total'):
                    print(f"  Total: {info['total']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())