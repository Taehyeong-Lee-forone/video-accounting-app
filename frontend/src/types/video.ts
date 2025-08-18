export interface Video {
  id: number
  filename: string
  gcs_uri?: string
  local_path?: string
  duration_ms?: number
  status: 'queued' | 'processing' | 'done' | 'error' | 'QUEUED' | 'PROCESSING' | 'DONE' | 'ERROR'
  progress?: number
  progress_message?: string
  error_message?: string
  created_at: string
  updated_at?: string
  receipts_count?: number
  auto_receipts_count?: number
  manual_receipts_count?: number
}