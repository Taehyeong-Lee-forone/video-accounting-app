'use client'

import { useRef, useState, useEffect } from 'react'
import { PlayIcon, PauseIcon, SpeakerWaveIcon, SpeakerXMarkIcon } from '@heroicons/react/24/solid'

interface Receipt {
  id: number
  vendor?: string
  total?: number
  best_frame?: {
    id?: number
    time_ms: number
  }
  best_frame_id?: number
  is_manual?: boolean
}

interface CustomVideoPlayerProps {
  url: string
  receipts?: Receipt[]
  onReceiptClick?: (receipt: Receipt) => void
  onTimeUpdate?: (time: number) => void
  onDuration?: (duration: number) => void
  videoRef?: React.MutableRefObject<HTMLVideoElement | null>
  seekToRef?: React.MutableRefObject<((time: number) => void) | null>
}

export default function CustomVideoPlayer({ 
  url, 
  receipts = [], 
  onReceiptClick,
  onTimeUpdate,
  onDuration,
  videoRef: externalVideoRef,
  seekToRef
}: CustomVideoPlayerProps) {
  const internalVideoRef = useRef<HTMLVideoElement>(null)
  const videoRef = externalVideoRef || internalVideoRef
  const progressBarRef = useRef<HTMLDivElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [isDragging, setIsDragging] = useState(false)
  const [hoveredReceipt, setHoveredReceipt] = useState<Receipt | null>(null)
  const [hoveredTime, setHoveredTime] = useState<number | null>(null)
  
  const controlsTimeoutRef = useRef<NodeJS.Timeout>()
  const seekTimeoutRef = useRef<NodeJS.Timeout>()

  // シーク機能を確実に実行する関数
  const seekTo = (targetTime: number) => {
    const video = videoRef.current
    if (!video) {
      console.error('Video element not found')
      return
    }

    // メタデータが読み込まれているかチェック
    if (!video.duration || isNaN(video.duration)) {
      console.warn('Video metadata not loaded yet, waiting...')
      
      // メタデータロードまで待機
      const handleMetadataLoaded = () => {
        video.removeEventListener('loadedmetadata', handleMetadataLoaded)
        performSeek(targetTime)
      }
      video.addEventListener('loadedmetadata', handleMetadataLoaded)
      
      // メタデータを強制的に読み込む
      video.load()
      return
    }

    // readyStateの詳細チェック
    // 0 = HAVE_NOTHING - メタデータなし
    // 1 = HAVE_METADATA - メタデータのみ
    // 2 = HAVE_CURRENT_DATA - 現在のフレームのみ
    // 3 = HAVE_FUTURE_DATA - 少なくとも次のフレームあり
    // 4 = HAVE_ENOUGH_DATA - 十分なデータあり
    if (video.readyState < 2) {
      console.warn(`Video not fully ready for seeking. readyState: ${video.readyState}, waiting...`)
      
      // readyStateが改善されるまで待機（条件を緩和）
      const waitForReady = () => {
        if (video.readyState >= 2 || video.duration) {
          console.log('Video is now ready, proceeding with seek')
          performSeek(targetTime)
        } else {
          setTimeout(waitForReady, 100)
        }
      }
      waitForReady()
      return
    }

    performSeek(targetTime)
  }

  // seekTo関数を外部から呼び出せるようにする
  useEffect(() => {
    if (seekToRef) {
      seekToRef.current = seekTo
    }
  }, [seekToRef])

  const performSeek = (targetTime: number) => {
    const video = videoRef.current
    if (!video) return

    console.log(`performSeek called with targetTime: ${targetTime}s, duration: ${video.duration}`)
    
    // 既存のタイムアウトをクリア
    if (seekTimeoutRef.current) {
      clearTimeout(seekTimeoutRef.current)
    }

    // 一時停止してからシーク（新規動画の場合に有効）
    const wasPlaying = !video.paused
    if (wasPlaying) {
      video.pause()
    }

    // メソッド1: fastSeekが利用可能な場合は使用
    if ('fastSeek' in video && typeof video.fastSeek === 'function') {
      try {
        (video as any).fastSeek(targetTime)
        console.log('Used fastSeek')
      } catch (e) {
        console.error('fastSeek failed:', e)
        video.currentTime = targetTime
      }
    } else {
      // メソッド2: 通常のcurrentTime設定
      video.currentTime = targetTime
    }

    // フォールバック: 少し待ってから再度設定
    seekTimeoutRef.current = setTimeout(() => {
      if (Math.abs(video.currentTime - targetTime) > 0.5) {
        console.log(`Seek didn't work properly, retrying. Current: ${video.currentTime}, Target: ${targetTime}`)
        video.currentTime = targetTime
      }
      
      // 元々再生中だった場合は再生を再開
      if (wasPlaying) {
        video.play()
      }
    }, 100)
  }

  // URLが変更されたときに動画を再ロード
  useEffect(() => {
    const video = videoRef.current
    if (!video || !url) return
    
    // 既存のシーク操作をクリア
    if (seekTimeoutRef.current) {
      clearTimeout(seekTimeoutRef.current)
    }

    // 動画をリセット
    setCurrentTime(0)
    setDuration(0)
    setIsPlaying(false)
    
    // 新しいURLをロード（srcが異なる場合のみ）
    if (video.src !== url) {
      video.src = url
      video.load()
    }
  }, [url])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleLoadedMetadata = () => {
      setDuration(video.duration)
      onDuration?.(video.duration)
    }
    
    const handleCanPlay = () => {
      // ビデオが再生可能になったことを確認
    }

    const handleLoadedData = () => {
      // ビデオデータロード完了
    }

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime)
      onTimeUpdate?.(video.currentTime)
    }

    const handleSeeked = () => {
      setCurrentTime(video.currentTime)
    }

    const handleSeeking = () => {
      // シーク中
    }

    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('canplay', handleCanPlay)
    video.addEventListener('loadeddata', handleLoadedData)
    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('seeked', handleSeeked)
    video.addEventListener('seeking', handleSeeking)

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('canplay', handleCanPlay)
      video.removeEventListener('loadeddata', handleLoadedData)
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('seeked', handleSeeked)
      video.removeEventListener('seeking', handleSeeking)
    }
  }, [onDuration, onTimeUpdate])

  const handlePlayPause = () => {
    const video = videoRef.current
    if (!video) return

    if (isPlaying) {
      video.pause()
    } else {
      video.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleProgressClick = (e: React.MouseEvent) => {
    const progressBar = progressBarRef.current
    if (!progressBar) {
      console.error('Progress bar not found')
      return
    }
    
    if (duration === 0) {
      console.error('Duration is 0, cannot seek')
      return
    }

    const rect = progressBar.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = Math.max(0, Math.min(1, x / rect.width))
    const newTime = percentage * duration
    
    console.log(`Progress bar click: seeking to ${newTime}s (${percentage * 100}% of ${duration}s)`)
    seekTo(newTime)
  }

  const handleProgressMouseMove = (e: React.MouseEvent) => {
    const progressBar = progressBarRef.current
    if (!progressBar) return

    const rect = progressBar.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = x / rect.width
    const time = percentage * duration
    
    setHoveredTime(time)

    // Check if hovering over a receipt
    const hovered = receipts.find(r => {
      if (!r.best_frame) return false
      const receiptTime = r.best_frame.time_ms / 1000
      return Math.abs(receiptTime - time) < 2 // within 2 seconds
    })
    setHoveredReceipt(hovered || null)
  }

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current
    if (!video) return

    const newVolume = parseFloat(e.target.value)
    setVolume(newVolume)
    video.volume = newVolume
    setIsMuted(newVolume === 0)
  }

  const toggleMute = () => {
    const video = videoRef.current
    if (!video) return

    if (isMuted) {
      video.volume = volume || 0.5
      setIsMuted(false)
    } else {
      video.volume = 0
      setIsMuted(true)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleMouseMove = () => {
    setShowControls(true)
    
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current)
    }
    
    controlsTimeoutRef.current = setTimeout(() => {
      if (isPlaying) {
        setShowControls(false)
      }
    }, 3000)
  }



  return (
    <div 
      className="relative bg-black rounded-lg overflow-hidden group w-full h-full"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => !isPlaying && setShowControls(true)}
    >
      <video
        ref={videoRef}
        src={url}
        className="w-full h-full object-contain"
        onClick={handlePlayPause}
        preload="metadata"
        crossOrigin="anonymous"
        playsInline
        muted
      />
      
      {/* Controls Overlay */}
      <div className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent transition-opacity duration-300 z-10 ${
        showControls ? 'opacity-100' : 'opacity-0'
      }`}>
        
        {/* Progress Bar with Receipts */}
        <div className="px-4 pb-2">
          {/* Timeline container with increased height for better visibility */}
          <div 
            ref={progressBarRef}
            className="relative h-2 bg-gray-700 rounded-full cursor-pointer group/progress"
            onClick={handleProgressClick}
            onMouseMove={handleProgressMouseMove}
            onMouseLeave={() => {
              setHoveredReceipt(null)
              setHoveredTime(null)
            }}
          >
            {/* Base progress track */}
            <div className="absolute inset-0 bg-gray-600/50 rounded-full" />
            
            {/* Receipt segments background */}
            {receipts.map((receipt, index) => {
              if (!receipt.best_frame) return null
              const position = (receipt.best_frame.time_ms / 1000 / duration) * 100
              const nextReceipt = receipts[index + 1]
              const segmentEnd = nextReceipt?.best_frame 
                ? (nextReceipt.best_frame.time_ms / 1000 / duration) * 100
                : 100
              
              return (
                <div key={`segment-${receipt.id}`}>
                  {/* Segment colored background */}
                  <div
                    className={`absolute top-0 h-full rounded-full transition-all cursor-pointer ${
                      receipt.is_manual 
                        ? 'bg-gradient-to-r from-green-500/30 to-green-400/20' 
                        : 'bg-gradient-to-r from-blue-500/30 to-blue-400/20'
                    } ${hoveredReceipt?.id === receipt.id ? '!from-opacity-60 !to-opacity-50' : ''}`}
                    style={{ 
                      left: `${position}%`,
                      width: `${segmentEnd - position}%`
                    }}
                    onClick={(e) => {
                      e.stopPropagation()
                      if (!receipt.best_frame || receipt.best_frame.time_ms === undefined) {
                        return
                      }
                      
                      const targetTime = receipt.best_frame.time_ms / 1000
                      seekTo(targetTime)
                    }}
                  />
                </div>
              )
            })}
            
            {/* Progress bar (played portion) */}
            <div 
              className="absolute left-0 top-0 h-full bg-gradient-to-r from-red-500 to-red-600 rounded-full shadow-sm"
              style={{ width: `${(currentTime / duration) * 100}%` }}
            />
            
            {/* Receipt markers as dots */}
            {receipts.map((receipt) => {
              if (!receipt.best_frame) return null
              const position = (receipt.best_frame.time_ms / 1000 / duration) * 100
              const isHovered = hoveredReceipt?.id === receipt.id
              
              return (
                <div key={`marker-${receipt.id}`}>
                  {/* Marker dot with clickable area */}
                  <div
                    className={`absolute top-1/2 -translate-y-1/2 transition-all cursor-pointer z-10 hover:scale-150`}
                    style={{ left: `${position}%`, transform: 'translate(-50%, -50%)' }}
                    onClick={(e) => {
                      e.stopPropagation()
                      if (!receipt.best_frame || receipt.best_frame.time_ms === undefined) {
                        return
                      }
                      
                      const targetTime = receipt.best_frame.time_ms / 1000
                      seekTo(targetTime)
                    }}
                    title={`${receipt.vendor || '領収書'} - ${(receipt.best_frame.time_ms / 1000).toFixed(1)}秒`}
                  >
                    {/* Invisible larger click area */}
                    <div className="absolute inset-0 -m-2"></div>
                    {/* Visible marker */}
                    <div className={`w-4 h-4 rounded-full border-2 border-white shadow-lg ${
                      receipt.is_manual 
                        ? 'bg-green-500 hover:bg-green-400' 
                        : 'bg-blue-500 hover:bg-blue-400'
                    } ${isHovered ? 'ring-4 ring-white/50 scale-125' : ''}`} />
                  </div>
                  
                  {/* Vertical line indicator on hover */}
                  {isHovered && (
                    <div
                      className="absolute -top-2 w-0.5 h-6 bg-white/60"
                      style={{ left: `${position}%`, transform: 'translateX(-50%)' }}
                    />
                  )}
                </div>
              )
            })}
            
            {/* Hover position indicator */}
            {hoveredTime !== null && !hoveredReceipt && (
              <div 
                className="absolute -top-1 w-0.5 h-4 bg-white/40"
                style={{ left: `${(hoveredTime / duration) * 100}%`, transform: 'translateX(-50%)' }}
              />
            )}
            
            {/* Current position scrubber */}
            <div 
              className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg ring-2 ring-red-500 transition-opacity opacity-0 group-hover/progress:opacity-100"
              style={{ left: `${(currentTime / duration) * 100}%`, transform: 'translate(-50%, -50%)' }}
            />
          </div>
          
          {/* Enhanced Hover Tooltip with thumbnail */}
          {hoveredReceipt && hoveredTime !== null && (
            <div 
              className="absolute bottom-full mb-3 bg-gray-900 text-white rounded-lg shadow-xl pointer-events-none z-20"
              style={{ left: `${(hoveredTime / duration) * 100}%`, transform: 'translateX(-50%)' }}
            >
              {/* Thumbnail if available */}
              {hoveredReceipt.best_frame && (
                <img 
                  src={`${process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'production' ? 'https://video-accounting-app.onrender.com' : 'http://localhost:5001')}/videos/frames/${hoveredReceipt.best_frame.id || hoveredReceipt.best_frame_id}/image`}
                  className="w-32 h-24 object-cover rounded-t-lg"
                  alt=""
                  onError={(e) => { e.currentTarget.style.display = 'none' }}
                />
              )}
              <div className="p-2">
                <div className="font-semibold text-sm">{hoveredReceipt.vendor || '領収書'}</div>
                <div className="text-xs text-gray-300">¥{hoveredReceipt.total?.toLocaleString() || 0}</div>
                <div className="text-xs text-gray-400 mt-1">
                  {hoveredReceipt.is_manual ? '手動追加' : '自動検出'}
                </div>
              </div>
              {/* Arrow pointing down */}
              <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900" />
            </div>
          )}
          
          {/* Legend for receipt types */}
          <div className="flex items-center gap-4 mt-2 text-xs text-white/60">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              <span>自動検出</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span>手動追加</span>
            </div>
          </div>
        </div>
        
        {/* Control Buttons */}
        <div className="flex items-center justify-between px-4 pb-3">
          <div className="flex items-center gap-3">
            {/* Play/Pause */}
            <button 
              onClick={handlePlayPause}
              className="text-white hover:text-gray-300 transition-colors"
            >
              {isPlaying ? (
                <PauseIcon className="h-6 w-6" />
              ) : (
                <PlayIcon className="h-6 w-6" />
              )}
            </button>
            
            {/* Volume */}
            <div className="flex items-center gap-2">
              <button 
                onClick={toggleMute}
                className="text-white hover:text-gray-300 transition-colors"
              >
                {isMuted ? (
                  <SpeakerXMarkIcon className="h-5 w-5" />
                ) : (
                  <SpeakerWaveIcon className="h-5 w-5" />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-20 accent-white"
              />
            </div>
            
            {/* Time Display */}
            <div className="text-white text-sm">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>
          </div>
          
          {/* Receipt Count */}
          {receipts.length > 0 && (
            <div className="text-white/70 text-xs">
              領収書: {receipts.length}件
            </div>
          )}
        </div>
      </div>
    </div>
  )
}