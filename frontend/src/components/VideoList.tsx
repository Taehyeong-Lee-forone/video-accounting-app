'use client'

import { useVideos } from '@/hooks/useVideos'
import Link from 'next/link'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import { FilmIcon, CheckCircleIcon, ClockIcon, ExclamationCircleIcon, TrashIcon } from '@heroicons/react/24/outline'
import { api, API_URL } from '@/lib/api'
import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { useVideoProgress } from '@/hooks/useVideoProgress'
import type { Video } from '@/types/video'

const statusConfig: Record<string, { label: string; icon: typeof ClockIcon; color: string }> = {
  queued: { label: '待機中', icon: ClockIcon, color: 'text-gray-500' },
  processing: { label: '処理中', icon: ClockIcon, color: 'text-blue-500' },
  done: { label: '完了', icon: CheckCircleIcon, color: 'text-green-500' },
  error: { label: 'エラー', icon: ExclamationCircleIcon, color: 'text-red-500' },
  // 大文字状態値も処理
  QUEUED: { label: '待機中', icon: ClockIcon, color: 'text-gray-500' },
  PROCESSING: { label: '処理中', icon: ClockIcon, color: 'text-blue-500' },
  DONE: { label: '完了', icon: CheckCircleIcon, color: 'text-green-500' },
  ERROR: { label: 'エラー', icon: ExclamationCircleIcon, color: 'text-red-500' },
}

export default function VideoList() {
  const { data: videos, isLoading, refetch } = useVideos()
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [processingVideoId, setProcessingVideoId] = useState<number | null>(null)
  
  const { progress, startPolling, stopPolling } = useVideoProgress(
    processingVideoId,
    processingVideoId !== null
  )
  
  // 処理中のビデオを検出してポーリング開始
  useEffect(() => {
    if (!videos) return
    
    const processingVideo = videos.find((video: any) => 
      video.status === 'processing' || video.status === 'PROCESSING'
    )
    
    if (processingVideo && processingVideoId !== processingVideo.id) {
      setProcessingVideoId(processingVideo.id)
      startPolling()
    } else if (!processingVideo && processingVideoId) {
      setProcessingVideoId(null)
      stopPolling()
      // 処理完了時にビデオリストをリフレッシュ
      refetch()
    }
  }, [videos, processingVideoId, startPolling, stopPolling, refetch])
  
  // 進捗率が更新されたらビデオリストも更新
  useEffect(() => {
    if (progress && (progress.status === 'done' || progress.status === 'DONE')) {
      refetch()
    }
  }, [progress, refetch])

  if (isLoading) {
    return (
      <div className="card">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const handleDelete = async (videoId: number) => {
    if (!confirm('この動画を削除してもよろしいですか？')) {
      return
    }
    
    setDeletingId(videoId)
    try {
      await api.delete(`/videos/${videoId}`)
      toast.success('動画を削除しました')
      refetch()
    } catch (error) {
      toast.error('削除に失敗しました')
    } finally {
      setDeletingId(null)
    }
  }

  if (!videos || videos.length === 0) {
    return (
      <div className="card text-center py-12">
        <FilmIcon className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-gray-500">動画がありません</p>
      </div>
    )
  }

  return (
    <div className="card">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">アップロード済み動画</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {videos.map((video: Video) => {
          const status = statusConfig[video.status] || statusConfig[video.status?.toLowerCase()] || statusConfig.error
          const StatusIcon = status?.icon || ExclamationCircleIcon
          
          return (
            <div
              key={video.id}
              className="border rounded-lg overflow-hidden hover:shadow-lg transition-all bg-white"
            >
              {/* サムネイル領域 */}
              <div className="relative aspect-video bg-gray-200">
                <img 
                  src={`${API_URL}/videos/${video.id}/thumbnail`}
                  alt={video.filename}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // サムネイル読み込み失敗時にデフォルトアイコン表示
                    e.currentTarget.style.display = 'none'
                    e.currentTarget.nextElementSibling?.classList.remove('hidden')
                  }}
                />
                <div className="hidden absolute inset-0 flex items-center justify-center bg-gray-100">
                  <FilmIcon className="h-16 w-16 text-gray-400" />
                </div>
                
                {/* ステータスバッジ */}
                <div className={`absolute top-2 right-2 px-2 py-1 rounded-full bg-white/90 backdrop-blur-sm ${status.color}`}>
                  <StatusIcon className="h-4 w-4 inline mr-1" />
                  <span className="text-xs font-medium text-gray-700">{status.label}</span>
                </div>
                
                {/* 領収書数（自動/手動区分） */}
                {(video.status === 'done' || video.status === 'DONE') && (
                  <div className="absolute bottom-2 left-2 flex gap-1">
                    {(video.auto_receipts_count || 0) > 0 && (
                      <div className="px-2 py-1 rounded-full bg-blue-600/80 text-white">
                        <span className="text-xs font-medium">🤖 {video.auto_receipts_count || 0}件</span>
                      </div>
                    )}
                    {(video.manual_receipts_count || 0) > 0 && (
                      <div className="px-2 py-1 rounded-full bg-green-600/80 text-white">
                        <span className="text-xs font-medium">✋ {video.manual_receipts_count || 0}件</span>
                      </div>
                    )}
                    {(video.receipts_count || 0) === 0 && (
                      <div className="px-2 py-1 rounded-full bg-gray-600/80 text-white">
                        <span className="text-xs font-medium">領収書なし</span>
                      </div>
                    )}
                  </div>
                )}
                
                {/* 進捗率表示 */}
                {(video.status === 'processing' || video.status === 'PROCESSING') && (
                  <div className="absolute bottom-0 left-0 right-0 bg-black/50 backdrop-blur-sm p-2">
                    <div className="w-full bg-gray-700 rounded-full h-1.5">
                      <div 
                        className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
                        style={{ 
                          width: `${(progress && processingVideoId === video.id) 
                            ? progress.progress
                            : video.progress || 0
                          }%` 
                        }}
                      />
                    </div>
                    <p className="text-xs text-white mt-1 truncate">
                      {(progress && processingVideoId === video.id) 
                        ? progress.progress_message || '処理中...'
                        : video.progress_message || '処理中...'}
                    </p>
                  </div>
                )}
              </div>
              
              {/* 情報領域 */}
              <div className="p-4">
                <h3 className="font-medium text-gray-900 truncate" title={video.filename}>
                  {video.filename}
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  {format(new Date(video.created_at), 'yyyy/MM/dd HH:mm', { locale: ja })}
                </p>
                
                {video.error_message && (
                  <p className="mt-2 text-xs text-red-600 line-clamp-2" title={video.error_message}>
                    {video.error_message}
                  </p>
                )}
                
                {/* 作業完了状態表示 */}
                {(video.status === 'done' || video.status === 'DONE') && (
                  <div className="mt-2 flex items-center gap-2">
                    {(video.receipts_count || 0) > 0 ? (
                      <>
                        <CheckCircleIcon className="h-4 w-4 text-green-600" />
                        <span className="text-xs text-green-600">分析完了</span>
                      </>
                    ) : (
                      <>
                        <ExclamationCircleIcon className="h-4 w-4 text-yellow-600" />
                        <span className="text-xs text-yellow-600">領収書未検出</span>
                      </>
                    )}
                  </div>
                )}
                
                {/* アクションボタン */}
                <div className="mt-3 flex gap-2">
                  {(video.status === 'done' || video.status === 'DONE') && (
                    <Link
                      href={`/review/${video.id}`}
                      className="flex-1 btn-primary text-center text-sm py-2"
                    >
                      仕訳確認
                    </Link>
                  )}
                  <button
                    onClick={() => handleDelete(video.id)}
                    disabled={deletingId === video.id}
                    className="btn-secondary text-red-600 hover:bg-red-50 disabled:opacity-50 p-2"
                    title="削除"
                  >
                    {deletingId === video.id ? (
                      <span className="animate-spin">⏳</span>
                    ) : (
                      <TrashIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}