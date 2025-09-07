'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { API_URL } from '@/lib/api'
import { PlayIcon, PauseIcon, CameraIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface VideoFrameSelectorProps {
  videoId: number
  videoPath?: string
  currentTimeMs: number
  duration: number
  onTimeChange: (timeMs: number) => void
  onFrameCapture?: (timeMs: number) => void
  className?: string
}

export default function VideoFrameSelector({
  videoId,
  videoPath,
  currentTimeMs,
  duration,
  onTimeChange,
  onFrameCapture,
  className = ''
}: VideoFrameSelectorProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const timelineRef = useRef<HTMLDivElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [localTimeMs, setLocalTimeMs] = useState(currentTimeMs)
  const [isVideoReady, setIsVideoReady] = useState(false)
  const dragStartX = useRef(0)
  const dragStartTime = useRef(0)

  // ビデオの準備状態を監視
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleLoadedMetadata = () => {
      setIsVideoReady(true)
      // 初期位置にシーク
      video.currentTime = currentTimeMs / 1000
    }

    const handleCanPlay = () => {
      setIsVideoReady(true)
    }

    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('canplay', handleCanPlay)

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('canplay', handleCanPlay)
    }
  }, [currentTimeMs])

  // currentTimeMsが外部から変更された時
  useEffect(() => {
    if (!isDragging && videoRef.current && isVideoReady) {
      videoRef.current.currentTime = currentTimeMs / 1000
      setLocalTimeMs(currentTimeMs)
    }
  }, [currentTimeMs, isDragging, isVideoReady])

  // ビデオ再生中の時間更新
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleTimeUpdate = () => {
      if (!isDragging && isPlaying) {
        const newTimeMs = Math.floor(video.currentTime * 1000)
        setLocalTimeMs(newTimeMs)
        onTimeChange(newTimeMs)
      }
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    return () => video.removeEventListener('timeupdate', handleTimeUpdate)
  }, [isDragging, isPlaying, onTimeChange])

  // 再生/一時停止
  const togglePlayPause = () => {
    const video = videoRef.current
    if (!video) return

    if (isPlaying) {
      video.pause()
      setIsPlaying(false)
    } else {
      video.play()
      setIsPlaying(true)
    }
  }

  // フレームキャプチャ
  const captureFrame = () => {
    if (onFrameCapture) {
      onFrameCapture(localTimeMs)
    }
  }

  // タイムラインのドラッグ開始
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!timelineRef.current || !videoRef.current) return
    
    setIsDragging(true)
    dragStartX.current = e.clientX
    dragStartTime.current = localTimeMs
    
    // ドラッグ中は再生を停止
    if (isPlaying) {
      videoRef.current.pause()
    }
    
    e.preventDefault()
  }

  // タイムラインのドラッグ中
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !timelineRef.current || !videoRef.current) return

    const rect = timelineRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
    const newTimeMs = Math.floor((percentage / 100) * duration * 1000)
    
    // リアルタイムでビデオをシーク
    videoRef.current.currentTime = newTimeMs / 1000
    setLocalTimeMs(newTimeMs)
  }, [isDragging, duration])

  // タイムラインのドラッグ終了
  const handleMouseUp = useCallback(() => {
    if (!isDragging) return
    
    setIsDragging(false)
    onTimeChange(localTimeMs)
    
    // ドラッグ前に再生中だった場合は再開
    if (isPlaying && videoRef.current) {
      videoRef.current.play()
    }
  }, [isDragging, localTimeMs, isPlaying, onTimeChange])

  // グローバルマウスイベント
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, handleMouseMove, handleMouseUp])

  // タイムラインクリック
  const handleTimelineClick = (e: React.MouseEvent) => {
    if (!timelineRef.current || !videoRef.current || isDragging) return
    
    const rect = timelineRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
    const newTimeMs = Math.floor((percentage / 100) * duration * 1000)
    
    videoRef.current.currentTime = newTimeMs / 1000
    setLocalTimeMs(newTimeMs)
    onTimeChange(newTimeMs)
  }

  // キーボードショートカット
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const video = videoRef.current
    if (!video) return

    switch(e.key) {
      case ' ':
        e.preventDefault()
        togglePlayPause()
        break
      case 'ArrowLeft':
        e.preventDefault()
        const prevTime = Math.max(0, video.currentTime - (e.shiftKey ? 1 : 0.1))
        video.currentTime = prevTime
        setLocalTimeMs(prevTime * 1000)
        onTimeChange(prevTime * 1000)
        break
      case 'ArrowRight':
        e.preventDefault()
        const nextTime = Math.min(duration, video.currentTime + (e.shiftKey ? 1 : 0.1))
        video.currentTime = nextTime
        setLocalTimeMs(nextTime * 1000)
        onTimeChange(nextTime * 1000)
        break
      case 'c':
        e.preventDefault()
        captureFrame()
        break
    }
  }

  const videoUrl = videoPath || `${API_URL}/videos/${videoId}/stream`

  return (
    <div className={`flex flex-col gap-2 ${className}`} onKeyDown={handleKeyDown} tabIndex={0}>
      {/* ビデオ表示エリア */}
      <div className="relative bg-black rounded-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          preload="metadata"
          playsInline
          muted
        />
        
        {/* オーバーレイコントロール */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {!isVideoReady && (
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
          )}
        </div>
        
        {/* 現在時間表示 */}
        <div className="absolute top-2 left-2 bg-black/70 text-white px-2 py-1 rounded text-sm font-mono">
          {(localTimeMs / 1000).toFixed(2)}s
        </div>
      </div>

      {/* コントロールバー */}
      <div className="bg-gray-100 rounded-lg p-2">
        {/* タイムライン */}
        <div 
          ref={timelineRef}
          className="relative h-8 bg-gray-300 rounded cursor-pointer mb-2"
          onMouseDown={handleMouseDown}
          onClick={handleTimelineClick}
        >
          {/* プログレスバー */}
          <div 
            className="absolute top-0 left-0 h-full bg-blue-500 rounded transition-none"
            style={{ 
              width: `${(localTimeMs / 1000 / duration) * 100}%`,
              pointerEvents: 'none'
            }}
          />
          
          {/* シークハンドル */}
          <div 
            className={`absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full border-2 border-blue-600 shadow-lg ${
              isDragging ? 'scale-125' : 'hover:scale-110'
            } transition-transform`}
            style={{ 
              left: `${(localTimeMs / 1000 / duration) * 100}%`,
              transform: 'translate(-50%, -50%)',
              pointerEvents: 'none'
            }}
          />
        </div>

        {/* ボタンコントロール */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* 再生/一時停止 */}
            <button
              onClick={togglePlayPause}
              className="p-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              title={isPlaying ? '一時停止 (Space)' : '再生 (Space)'}
            >
              {isPlaying ? (
                <PauseIcon className="h-5 w-5" />
              ) : (
                <PlayIcon className="h-5 w-5" />
              )}
            </button>

            {/* 時間表示 */}
            <span className="text-sm font-medium text-gray-700">
              {(localTimeMs / 1000).toFixed(1)}s / {duration.toFixed(1)}s
            </span>
          </div>

          {/* フレームキャプチャボタン */}
          {onFrameCapture && (
            <button
              onClick={captureFrame}
              className="flex items-center gap-1 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
              title="フレームキャプチャ (C)"
            >
              <CameraIcon className="h-4 w-4" />
              キャプチャ
            </button>
          )}
        </div>

        {/* ショートカットヘルプ */}
        <div className="mt-2 text-xs text-gray-500">
          Space: 再生/停止 | ←→: 0.1秒移動 | Shift+←→: 1秒移動 | C: キャプチャ
        </div>
      </div>
    </div>
  )
}