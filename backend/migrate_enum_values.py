#!/usr/bin/env python3
"""
PostgreSQL enum値を安全に変更するマイグレーションスクリプト

使用方法:
1. ローカルでテスト: python migrate_enum_values.py
2. 本番環境で実行: DATABASE_URL=your_prod_url python migrate_enum_values.py --apply
"""
import os
import sys
import argparse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def migrate_video_status_enum(engine, dry_run=True):
    """
    video_status enumを'QUEUED'から'queued'に変更する
    
    Args:
        engine: SQLAlchemy engine
        dry_run: Trueの場合は変更を適用せず、確認のみ
    """
    
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}video_status enum マイグレーション開始")
    
    try:
        with engine.begin() as conn:
            # 現在のenum値を確認
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'video_status'
                ORDER BY enumsortorder;
            """))
            
            current_values = [row[0] for row in result.fetchall()]
            logger.info(f"現在のenum値: {current_values}")
            
            # 既存データの確認
            result = conn.execute(text("""
                SELECT status, COUNT(*) as count
                FROM videos 
                GROUP BY status 
                ORDER BY status;
            """))
            
            data_counts = {row[0]: row[1] for row in result.fetchall()}
            logger.info(f"既存データの分布: {data_counts}")
            
            # マイグレーションが必要かチェック
            needs_migration = False
            migration_steps = []
            
            if 'QUEUED' in current_values and 'QUEUED' in data_counts:
                needs_migration = True
                logger.info(f"'QUEUED'データが{data_counts['QUEUED']}件見つかりました")
                
                # ステップ1: 'queued'値を追加（まだ存在しない場合）
                if 'queued' not in current_values:
                    migration_steps.append("ALTER TYPE video_status ADD VALUE 'queued';")
                
                # ステップ2: 既存データを更新
                migration_steps.append("UPDATE videos SET status = 'queued'::video_status WHERE status = 'QUEUED'::video_status;")
                
                # ステップ3: 古い値を削除（PostgreSQLではenum値の削除は複雑なため、後で手動実行）
                logger.warning("注意: 'QUEUED'値の削除は手動で行う必要があります（enum値削除は複雑なため）")
            
            if not needs_migration:
                logger.info("✅ マイグレーションは不要です")
                return True
            
            logger.info("実行予定のマイグレーション:")
            for i, step in enumerate(migration_steps, 1):
                logger.info(f"  {i}. {step}")
            
            if dry_run:
                logger.info("[DRY RUN] 実際の変更は行いません")
                return True
            
            # 実際のマイグレーション実行
            logger.info("マイグレーションを実行中...")
            for i, step in enumerate(migration_steps, 1):
                logger.info(f"実行中 {i}/{len(migration_steps)}: {step}")
                conn.execute(text(step))
                logger.info(f"✅ ステップ{i}完了")
            
            # 結果確認
            result = conn.execute(text("""
                SELECT status, COUNT(*) as count
                FROM videos 
                GROUP BY status 
                ORDER BY status;
            """))
            
            final_counts = {row[0]: row[1] for row in result.fetchall()}
            logger.info(f"マイグレーション後のデータ分布: {final_counts}")
            
            logger.info("✅ マイグレーション完了")
            return True
            
    except Exception as e:
        logger.error(f"❌ マイグレーションエラー: {e}")
        return False

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='PostgreSQL enum マイグレーション')
    parser.add_argument('--apply', action='store_true', 
                       help='実際に変更を適用する（デフォルトはdry-run）')
    parser.add_argument('--database-url', type=str,
                       help='データベースURL（環境変数DATABASE_URLより優先）')
    
    args = parser.parse_args()
    
    # DATABASE_URL取得
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URLが設定されていません")
        sys.exit(1)
    
    # 安全確認
    if args.apply:
        logger.warning("⚠️  実際の変更を適用します")
        confirm = input("続行しますか？ (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            logger.info("操作をキャンセルしました")
            sys.exit(0)
    else:
        logger.info("🔍 DRY RUNモード（変更は適用されません）")
    
    try:
        # データベース接続
        engine = create_engine(database_url)
        logger.info("データベースに接続しました")
        
        # マイグレーション実行
        success = migrate_video_status_enum(engine, dry_run=not args.apply)
        
        if success:
            logger.info("✅ 処理完了")
            sys.exit(0)
        else:
            logger.error("❌ 処理失敗")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ 接続エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()