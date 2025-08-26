"""
画像前処理ユーティリティ
OCR精度向上のための画像前処理
"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import io

class ImagePreprocessor:
    """OCR用画像前処理クラス"""
    
    @staticmethod
    def preprocess_for_ocr(image_path: str, output_path: str = None) -> str:
        """
        OCR用に画像を前処理
        - コントラスト強化
        - ノイズ除去
        - 二値化
        - 傾き補正
        """
        # OpenCVで画像読み込み
        img = cv2.imread(image_path)
        
        # グレースケール変換
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # ノイズ除去（ガウシアンブラー）
        denoised = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # コントラスト強化（CLAHE）
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # 適応的二値化
        binary = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        # 傾き補正
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) > 0.5:  # 0.5度以上の傾きがある場合のみ補正
                (h, w) = binary.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                binary = cv2.warpAffine(
                    binary, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
        
        # 保存先パス
        if output_path is None:
            output_path = image_path.replace('.', '_preprocessed.')
        
        # 保存
        cv2.imwrite(output_path, binary)
        return output_path
    
    @staticmethod
    def enhance_receipt_image(image_path: str) -> str:
        """
        レシート画像の強化（PILベース）
        """
        # PIL画像として開く
        img = Image.open(image_path)
        
        # RGB変換（必要な場合）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # コントラスト強化
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # シャープネス強化
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)
        
        # 明度調整
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        
        # エッジ強調
        img = img.filter(ImageFilter.EDGE_ENHANCE)
        
        # 保存
        output_path = image_path.replace('.', '_enhanced.')
        img.save(output_path, quality=95)
        return output_path
    
    @staticmethod
    def resize_for_ocr(image_path: str, target_width: int = 2000) -> str:
        """
        OCR用に画像をリサイズ（解像度向上）
        """
        img = Image.open(image_path)
        
        # 現在のサイズ取得
        width, height = img.size
        
        # 小さすぎる場合は拡大
        if width < target_width:
            ratio = target_width / width
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # LANCZOS補間で高品質リサイズ
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            output_path = image_path.replace('.', '_resized.')
            img.save(output_path, quality=95)
            return output_path
        
        return image_path