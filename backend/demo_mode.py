"""
デモモード管理
"""
import os
from fastapi import HTTPException

def is_demo_mode() -> bool:
    """デモモードかどうかを確認"""
    return os.getenv("DEMO_MODE", "false").lower() == "true"

def check_demo_restrictions(operation: str):
    """デモモードの制限をチェック"""
    if not is_demo_mode():
        return
    
    restricted_operations = [
        "upload_video",
        "delete_video", 
        "delete_receipt",
        "delete_journal",
        "update_master"
    ]
    
    if operation in restricted_operations:
        raise HTTPException(
            status_code=403,
            detail="🎯 デモモードでは、この操作は無効です。既存のサンプルデータをご覧ください。"
        )

def get_demo_info():
    """デモモード情報を取得"""
    if is_demo_mode():
        return {
            "is_demo": True,
            "message": os.getenv("DEMO_MESSAGE", "デモモードで実行中"),
            "restrictions": [
                "新規動画アップロード不可",
                "データの削除不可",
                "マスタデータの変更不可"
            ],
            "available_features": [
                "既存動画の閲覧",
                "領収書分析結果の確認",
                "仕訳データの確認・編集",
                "CSVエクスポート"
            ]
        }
    return {"is_demo": False}