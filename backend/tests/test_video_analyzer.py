import pytest
import numpy as np
from unittest.mock import Mock, patch
from services.video_intelligence import VideoAnalyzer

def test_normalize_text():
    """テキスト正規化のテスト"""
    analyzer = VideoAnalyzer()
    
    # 全角→半角変換
    assert analyzer._normalize_text("１２３ＡＢＣ") == "123abc"
    
    # スペース・記号削除
    assert analyzer._normalize_text("test @ 123 # abc") == "test123abc"
    
    # 日本語はそのまま
    text = "領収書123円"
    normalized = analyzer._normalize_text(text)
    assert "領収書" in normalized
    assert "123" in normalized

def test_frame_score_calculation():
    """フレームスコア計算のテスト"""
    analyzer = VideoAnalyzer()
    
    # モックフレームデータ
    with patch('cv2.imread') as mock_imread, \
         patch('cv2.cvtColor') as mock_cvtcolor, \
         patch('cv2.Laplacian') as mock_laplacian, \
         patch('numpy.mean') as mock_mean, \
         patch('numpy.std') as mock_std, \
         patch('PIL.Image.open') as mock_pil_open, \
         patch('imagehash.phash') as mock_phash:
        
        # モック設定
        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imread.return_value = mock_img
        mock_cvtcolor.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_laplacian.return_value = Mock(var=Mock(return_value=500))
        mock_mean.return_value = 128  # 理想的な明るさ
        mock_std.return_value = 30   # 適度なコントラスト
        mock_phash.return_value = "test_hash"
        mock_pil_open.return_value = Mock()
        
        result = analyzer._analyze_frame("test.jpg", 1000)
        
        assert result['time_ms'] == 1000
        assert result['sharpness'] == 500
        assert result['brightness'] == 128
        assert result['contrast'] == 30
        assert result['phash'] == "test_hash"
        assert 0 <= result['frame_score'] <= 1

def test_best_frame_selection():
    """ベストフレーム選定のテスト"""
    analyzer = VideoAnalyzer()
    
    frames = [
        {'frame_score': 0.5, 'ocr_text': 'short'},
        {'frame_score': 0.7, 'ocr_text': 'medium text here'},
        {'frame_score': 0.6, 'ocr_text': 'very long text with lots of content that should boost the score significantly'},
    ]
    
    best = analyzer.select_best_frame(frames)
    
    # OCRテキスト量を考慮した選定
    assert best is not None
    assert 'final_score' in best

def test_duplicate_detection():
    """重複検出のテスト"""
    analyzer = VideoAnalyzer()
    
    existing_receipts = [
        {'id': 1, 'phash': '0000000000000000', 'normalized_text_hash': 'hash1'},
        {'id': 2, 'phash': '1111111111111111', 'normalized_text_hash': 'hash2'},
    ]
    
    # pHash距離による検出
    with patch('imagehash.hex_to_hash') as mock_hex_to_hash:
        mock_hex_to_hash.side_effect = [
            Mock(__sub__=Mock(return_value=3)),  # 近い
            Mock(__sub__=Mock(return_value=3)),
            Mock(__sub__=Mock(return_value=10)), # 遠い
            Mock(__sub__=Mock(return_value=10)),
        ]
        
        duplicate_id = analyzer.check_duplicate(
            '0000000000000001',
            'different text',
            existing_receipts
        )
        
        assert duplicate_id == 1  # 最初のレシートと重複

if __name__ == "__main__":
    pytest.main([__file__])