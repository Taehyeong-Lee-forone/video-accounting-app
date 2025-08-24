import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'

interface VideoProgress {
  id: number
  status: string
  progress: number
  progress_message: string
  error_message?: string
}

export function useVideoProgress(videoId: number | null, enabled: boolean = false) {
  const [progress, setProgress] = useState<VideoProgress | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const fetchProgress = useCallback(async () => {
    if (!videoId) return

    try {
      const response = await api.get(`/videos/${videoId}`)
      const videoData = response.data
      
      setProgress({
        id: videoData.id,
        status: videoData.status,
        progress: videoData.progress || 0,
        progress_message: videoData.progress_message || '',
        error_message: videoData.error_message
      })

      // 完了またはエラーが発生したらポーリング停止
      if (videoData.status === 'done' || videoData.status === 'DONE' || 
          videoData.status === 'error' || videoData.status === 'ERROR') {
        setIsPolling(false)
      }
    } catch (error) {
      console.error('Failed to fetch video progress:', error)
      setIsPolling(false)
    }
  }, [videoId])

  const startPolling = useCallback(() => {
    setIsPolling(true)
  }, [])

  const stopPolling = useCallback(() => {
    setIsPolling(false)
  }, [])

  // ポーリングロジック
  useEffect(() => {
    if (!enabled || !isPolling || !videoId) return

    // 即座に一度実行
    fetchProgress()

    // 2秒ごとにポーリング
    const interval = setInterval(fetchProgress, 2000)

    return () => clearInterval(interval)
  }, [enabled, isPolling, videoId, fetchProgress])

  return {
    progress,
    isPolling,
    startPolling,
    stopPolling,
    fetchProgress
  }
}