-- 新しいフレーム追跡フィールドを追加するマイグレーション
-- Add new frame tracking fields migration

-- Add new columns to frames table (SQLite doesn't support IF NOT EXISTS for columns)
ALTER TABLE frames ADD COLUMN dhash VARCHAR(64);
ALTER TABLE frames ADD COLUMN doc_quad_json TEXT;
ALTER TABLE frames ADD COLUMN sharpness_score FLOAT;
ALTER TABLE frames ADD COLUMN doc_area_score FLOAT;
ALTER TABLE frames ADD COLUMN perspective_score FLOAT;
ALTER TABLE frames ADD COLUMN exposure_score FLOAT;
ALTER TABLE frames ADD COLUMN stability_score FLOAT;
ALTER TABLE frames ADD COLUMN glare_penalty FLOAT;
ALTER TABLE frames ADD COLUMN textness_score FLOAT;
ALTER TABLE frames ADD COLUMN total_quality_score FLOAT;
ALTER TABLE frames ADD COLUMN motion_score FLOAT;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_frame_dhash ON frames(dhash);
CREATE INDEX IF NOT EXISTS idx_frame_quality_score ON frames(total_quality_score);
CREATE INDEX IF NOT EXISTS idx_frame_doc_area ON frames(doc_area_score);

-- Update existing rows with default values (optional)
UPDATE frames 
SET total_quality_score = frame_score 
WHERE total_quality_score IS NULL AND frame_score IS NOT NULL;