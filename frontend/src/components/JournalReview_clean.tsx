'use client'

import { useState, useRef, useEffect } from 'react'
import { useVideoDetail } from '@/hooks/useVideoDetail'
import { useJournals } from '@/hooks/useJournals'
import { api, API_URL } from '@/lib/api'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import ReactPlayer from 'react-player'
import JournalTable from './JournalTable'
import { ArrowDownTrayIcon, CameraIcon, PlusIcon, XMarkIcon, PencilIcon, CheckIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline'

interface JournalReviewProps {
  videoId: number
}

export default function JournalReview({ videoId }: JournalReviewProps) {
  const { data: video, isLoading: videoLoading } = useVideoDetail(videoId)
  const { data: journals, isLoading: journalsLoading, refetch } = useJournals(videoId)
  const [selectedJournal, setSelectedJournal] = useState<any>(null)
  const [selectedReceipt, setSelectedReceipt] = useState<any>(null)
  const [playerReady, setPlayerReady] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [videoDuration, setVideoDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [hoveredReceiptId, setHoveredReceiptId] = useState<number | null>(null)
  const [editingReceiptId, setEditingReceiptId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<any>({})
  const [showHistory, setShowHistory] = useState<number | null>(null)
  const playerRef = useRef<ReactPlayer>(null)

  const handleJournalClick = (journal: any) => {
    setSelectedJournal(journal)
    
    if (!journal.time_ms) {
      console.log('No timestamp for this journal')
      return
    }
    
    if (!playerRef.current || !playerReady) {
      console.error('Player not ready for seeking')
      return
    }
    
    const seconds = journal.time_ms / 1000
    console.log(`Journal click: seeking to ${seconds}s (${journal.time_ms}ms)`)
    
    // seekToを2回呼ぶことで確実にシークする
    playerRef.current.seekTo(seconds)
    setTimeout(() => {
      if (playerRef.current) {
        playerRef.current.seekTo(seconds)
      }
    }, 50)
  }

  const handleReceiptClick = (receipt: any) => {
    setSelectedReceipt(receipt)
    
    if (receipt.best_frame?.time_ms === undefined) {
      console.log('No timestamp for this receipt')
      return
    }
    
    if (!playerRef.current || !playerReady) {
      console.error('Player not ready for seeking')
      return
    }
    
    const seconds = receipt.best_frame.time_ms / 1000
    console.log(`Receipt click: seeking to ${seconds}s (${receipt.best_frame.time_ms}ms)`)
    
    try {
      // seekToを2回呼ぶことで確実にシークする
      playerRef.current.seekTo(seconds)
      setTimeout(() => {
        if (playerRef.current) {
          playerRef.current.seekTo(seconds)
        }
      }, 50)
    } catch (e) {
      console.error('Seek failed:', e)
    }
  }

  const handlePlayerReady = () => {
    console.log('Player is ready')
    setPlayerReady(true)
    // getDurationを少し遅らせて確実に取得
    setTimeout(() => {
      if (playerRef.current) {
        const duration = playerRef.current.getDuration()
        console.log('Video duration:', duration)
        setVideoDuration(duration)
      }
    }, 100)
  }

  const handleProgress = (state: { played: number; playedSeconds: number }) => {
    setCurrentTime(state.playedSeconds)
  }

  const handleDuration = (duration: number) => {
    setVideoDuration(duration)
  }

  const handleMarkerClick = (timeMs: number) => {
    if (!playerRef.current) {
      console.error('Player ref not available')
      return
    }
    if (!playerReady) {
      console.error('Player not ready')
      return
    }
    
    const seconds = timeMs / 1000
    console.log(`Marker click: seeking to ${seconds}s (${timeMs}ms)`)
    
    // seekToを2回呼ぶことで確実にシークする
    playerRef.current.seekTo(seconds)
    setTimeout(() => {
      if (playerRef.current) {
        playerRef.current.seekTo(seconds)
      }
    }, 50)
  }

  const handleAnalyzeCurrentFrame = async () => {
    if (!playerRef.current || !playerReady) {
      toast.error('動画プレイヤーが準備できていません')
      return
    }

    try {
      setIsAnalyzing(true)
      
      const currentTime = playerRef.current.getCurrentTime()
      const timeMs = Math.floor(currentTime * 1000)
      
      const response = await api.post(`/videos/${videoId}/analyze-frame`, null, {
        params: { time_ms: timeMs }
      })
      
      if (response.data.receipt_id) {
        toast.success(`フレーム分析完了: ${timeMs}ms`)
        window.location.reload()
      } else {
        toast.warning('領収書データを抽出できませんでした')
      }
    } catch (error: any) {
      console.error('Frame analysis error:', error)
      toast.error(error.response?.data?.detail || 'フレーム分析に失敗しました')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleEditReceipt = (receipt: any, event?: React.MouseEvent) => {
    if (event) event.stopPropagation()
    
    setEditingReceiptId(receipt.id)
    setEditForm({
      vendor: receipt.vendor || '',
      total: receipt.total || 0,
      tax: receipt.tax || 0,
      issue_date: receipt.issue_date ? format(new Date(receipt.issue_date), 'yyyy-MM-dd') : '',
      payment_method: receipt.payment_method || '',
      memo: receipt.memo || ''
    })
  }

  const handleSaveEdit = async (receiptId: number, event?: React.MouseEvent) => {
    if (event) event.stopPropagation()
    
    try {
      const updateData = {
        ...editForm,
        issue_date: editForm.issue_date ? new Date(editForm.issue_date).toISOString() : null,
        total: parseFloat(editForm.total) || 0,
        tax: parseFloat(editForm.tax) || 0
      }
      
      await api.patch(`/videos/${videoId}/receipts/${receiptId}`, updateData)
      toast.success('領収書を更新しました')
      
      setEditingReceiptId(null)
      setEditForm({})
      
      window.location.reload()
    } catch (error: any) {
      console.error('Update receipt error:', error)
      toast.error(error.response?.data?.detail || '更新に失敗しました')
    }
  }

  const handleCancelEdit = (event?: React.MouseEvent) => {
    if (event) event.stopPropagation()
    setEditingReceiptId(null)
    setEditForm({})
  }

  const handleShowHistory = async (receiptId: number, event?: React.MouseEvent) => {
    if (event) event.stopPropagation()
    
    if (showHistory === receiptId) {
      setShowHistory(null)
    } else {
      setShowHistory(receiptId)
      
      try {
        const response = await api.get(`/videos/${videoId}/receipts/${receiptId}/history`)
        console.log('History data:', response.data)
      } catch (error) {
        console.error('Failed to fetch history:', error)
      }
    }
  }

  const handleDeleteReceipt = async (receiptId: number, event: React.MouseEvent) => {
    event.stopPropagation()
    
    const confirmMessage = '本当にこの領収書を削除しますか？\n関連する仕訳データも削除されます。'
    if (!confirm(confirmMessage)) {
      return
    }
    
    try {
      await api.delete(`/videos/${videoId}/receipts/${receiptId}`)
      toast.success('領収書を削除しました')
      window.location.reload()
    } catch (error: any) {
      console.error('Delete receipt error:', error)
      toast.error(error.response?.data?.detail || '削除に失敗しました')
    }
  }

  const handleConfirm = async (journalId: number) => {
    try {
      await api.post(`/journals/${journalId}/confirm`, {
        confirmed_by: 'user'
      })
      toast.success('仕訳を確認しました')
      refetch()
    } catch (error) {
      toast.error('確認に失敗しました')
    }
  }

  const handleReject = async (journalId: number) => {
    try {
      await api.post(`/journals/${journalId}/reject`)
      toast.success('仕訳を差戻しました')
      refetch()
    } catch (error) {
      toast.error('差戻しに失敗しました')
    }
  }

  const handleUpdate = async (journalId: number, data: any) => {
    try {
      await api.patch(`/journals/${journalId}`, data)
      toast.success('仕訳を更新しました')
      refetch()
    } catch (error) {
      toast.error('更新に失敗しました')
    }
  }

  const handleExportCSV = async () => {
    try {
      const response = await api.get(`/export/csv?video_id=${videoId}`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `journal_export_${videoId}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      
      toast.success('CSVをダウンロードしました')
    } catch (error) {
      toast.error('エクスポートに失敗しました')
    }
  }

  if (videoLoading || journalsLoading) {
    return <div className="card">読み込み中...</div>
  }

  if (!video) {
    return <div className="card">動画が見つかりません</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">仕訳レビュー</h1>
        <button
          onClick={handleExportCSV}
          className="btn-primary flex items-center"
        >
          <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
          CSV出力
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 動画プレイヤー - 左側に固定 */}
        <div className="lg:sticky lg:top-6" style={{ height: 'fit-content', alignSelf: 'start' }}>
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">動画</h2>
            <div className="relative">
              <ReactPlayer
                ref={playerRef}
                url={video.local_path ? `${API_URL}/${video.local_path}` : ''}
                controls
                width="100%"
                height="400px"
                onReady={handlePlayerReady}
                onProgress={handleProgress}
                onDuration={handleDuration}
                progressInterval={100}
                playing={false}
                pip={false}
                config={{
                  file: {
                    attributes: {
                      controlsList: 'nodownload',
                      preload: 'metadata'
                    }
                  }
                }}
              />
            </div>
            
            {/* タイムラインマーカー */}
            {videoDuration > 0 && video.receipts && video.receipts.length > 0 && (
              <div className="mt-3">
                <div className="text-xs text-gray-600 mb-1">領収書タイムライン:</div>
                <div 
                  className="relative bg-gray-200 h-8 rounded-lg overflow-hidden cursor-pointer"
                  onClick={(e) => {
                    if (!playerRef.current || !playerReady || videoDuration === 0) {
                      console.error('Cannot seek: player not ready or duration is 0')
                      return
                    }
                    
                    const rect = e.currentTarget.getBoundingClientRect()
                    const x = e.clientX - rect.left
                    const percentage = Math.max(0, Math.min(1, x / rect.width))
                    const targetTime = percentage * videoDuration
                    
                    console.log(`Timeline click: seeking to ${targetTime}s (${percentage * 100}%)`)
                    
                    // seekToを2回呼ぶことで確実にシークする
                    playerRef.current.seekTo(targetTime)
                    setTimeout(() => {
                      if (playerRef.current) {
                        playerRef.current.seekTo(targetTime)
                      }
                    }, 50)
                  }}
                >
                  <div 
                    className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 pointer-events-none"
                    style={{ left: `${(currentTime / videoDuration) * 100}%` }}
                  />
                  
                  {video.receipts.map((receipt: any) => {
                    if (!receipt.best_frame?.time_ms) return null
                    const position = (receipt.best_frame.time_ms / 1000 / videoDuration) * 100
                    
                    return (
                      <div
                        key={receipt.id}
                        className={`absolute top-1 bottom-1 w-2 rounded-full cursor-pointer transform -translate-x-1/2 transition-all hover:scale-125 z-10 ${
                          receipt.is_manual ? 'bg-green-500' : 'bg-blue-500'
                        } ${selectedReceipt?.id === receipt.id ? 'ring-2 ring-yellow-400' : ''}`}
                        style={{ left: `${position}%` }}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleMarkerClick(receipt.best_frame.time_ms)
                        }}
                        title={`${receipt.vendor || '不明'} - ${Math.floor(receipt.best_frame.time_ms / 1000)}秒${
                          receipt.is_manual ? ' (手動追加)' : ''
                        }`}
                      />
                    )
                  })}
                </div>
              </div>
            )}
            
            <div className="mt-4">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleAnalyzeCurrentFrame}
                  disabled={isAnalyzing || !playerReady}
                  className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    isAnalyzing || !playerReady
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {isAnalyzing ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      分析中...
                    </>
                  ) : (
                    <>
                      <CameraIcon className="h-4 w-4 mr-2" />
                      現在のフレームを分析
                    </>
                  )}
                </button>
                <span className="text-xs text-gray-500">
                  動画を一時停止して、分析したい位置で使用してください
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 領収書情報 - 右側でスクロール可能 */}
        <div className="card overflow-hidden flex flex-col" style={{ height: 'calc(100vh - 200px)', maxHeight: '800px' }}>
          <h2 className="text-xl font-semibold mb-4 flex-shrink-0">領収書情報</h2>
          {video.receipts && video.receipts.length > 0 ? (
            <div className="space-y-4 overflow-y-auto pr-3 custom-scrollbar" style={{ flex: 1 }}>
              {[...video.receipts]
                .sort((a, b) => {
                  const timeA = a.best_frame?.time_ms || 0
                  const timeB = b.best_frame?.time_ms || 0
                  return timeA - timeB
                })
                .map((receipt: any, index: number) => (
                <div 
                  key={receipt.id} 
                  className={`relative border rounded-lg p-4 cursor-pointer transition-all group ${
                    selectedReceipt?.id === receipt.id 
                      ? 'border-blue-500 bg-blue-50 shadow-md' 
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => handleReceiptClick(receipt)}
                  onMouseEnter={() => setHoveredReceiptId(receipt.id)}
                  onMouseLeave={() => setHoveredReceiptId(null)}
                  title="クリックして動画を該当時刻へ移動"
                >
                  <div className="absolute top-2 left-2 w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center text-xs font-medium text-gray-700">
                    {index + 1}
                  </div>
                  
                  {/* アクションボタン */}
                  <div className={`absolute top-2 right-2 flex gap-1 transition-all ${
                    hoveredReceiptId === receipt.id || selectedReceipt?.id === receipt.id || editingReceiptId === receipt.id
                      ? 'opacity-100'
                      : 'opacity-0 pointer-events-none'
                  }`}>
                    {editingReceiptId === receipt.id ? (
                      <>
                        <button
                          onClick={(e) => handleSaveEdit(receipt.id, e)}
                          className="p-1.5 rounded-lg bg-green-50 hover:bg-green-100 transition-colors"
                          title="保存"
                        >
                          <CheckIcon className="h-5 w-5 text-green-600" />
                        </button>
                        <button
                          onClick={(e) => handleCancelEdit(e)}
                          className="p-1.5 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
                          title="キャンセル"
                        >
                          <XCircleIcon className="h-5 w-5 text-gray-600" />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={(e) => handleEditReceipt(receipt, e)}
                          className="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 transition-colors"
                          title="編集"
                        >
                          <PencilIcon className="h-5 w-5 text-blue-600" />
                        </button>
                        <button
                          onClick={(e) => handleShowHistory(receipt.id, e)}
                          className="p-1.5 rounded-lg bg-yellow-50 hover:bg-yellow-100 transition-colors"
                          title="修正履歴"
                        >
                          <ClockIcon className="h-5 w-5 text-yellow-600" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteReceipt(receipt.id, e)}
                          className="p-1.5 rounded-lg bg-red-50 hover:bg-red-100 transition-colors"
                          title="削除"
                        >
                          <XMarkIcon className="h-5 w-5 text-red-600" />
                        </button>
                      </>
                    )}
                  </div>
                  
                  {/* 手動追加バッジ */}
                  <div className="ml-8 mb-3">
                    {receipt.is_manual && (
                      <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <PlusIcon className="h-3 w-3 mr-1" />
                        手動追加
                      </div>
                    )}
                  </div>
                  
                  {/* プレビュー画像とタイムスタンプ */}
                  {receipt.best_frame && (
                    <div className="mb-4 flex items-start gap-4">
                      <div className="flex-shrink-0">
                        <img 
                          src={`${API_URL}/videos/frames/${receipt.best_frame.id}/image`}
                          alt={`Frame at ${receipt.best_frame.time_ms}ms`}
                          className="w-32 h-24 object-cover rounded border"
                        />
                        <div className="text-xs text-gray-500 mt-1">
                          {Math.floor(receipt.best_frame.time_ms / 1000)}秒 ({receipt.best_frame.time_ms}ms)
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="font-medium">ベンダー:</span>{' '}
                      {editingReceiptId === receipt.id ? (
                        <input
                          type="text"
                          value={editForm.vendor}
                          onChange={(e) => setEditForm({...editForm, vendor: e.target.value})}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-block w-32 px-1 py-0.5 text-sm border rounded"
                        />
                      ) : (
                        receipt.vendor || '-'
                      )}
                    </div>
                    <div>
                      <span className="font-medium">日付:</span>{' '}
                      {editingReceiptId === receipt.id ? (
                        <input
                          type="date"
                          value={editForm.issue_date}
                          onChange={(e) => setEditForm({...editForm, issue_date: e.target.value})}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-block px-1 py-0.5 text-sm border rounded"
                        />
                      ) : (
                        receipt.issue_date
                          ? format(new Date(receipt.issue_date), 'yyyy/MM/dd', { locale: ja })
                          : '-'
                      )}
                    </div>
                    <div>
                      <span className="font-medium">合計:</span>{' '}
                      {editingReceiptId === receipt.id ? (
                        <>
                          ¥<input
                            type="number"
                            value={editForm.total}
                            onChange={(e) => setEditForm({...editForm, total: e.target.value})}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-block w-24 px-1 py-0.5 text-sm border rounded"
                          />
                        </>
                      ) : (
                        `¥${receipt.total?.toLocaleString() || '0'}`
                      )}
                    </div>
                    <div>
                      <span className="font-medium">税額:</span>{' '}
                      {editingReceiptId === receipt.id ? (
                        <>
                          ¥<input
                            type="number"
                            value={editForm.tax}
                            onChange={(e) => setEditForm({...editForm, tax: e.target.value})}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-block w-20 px-1 py-0.5 text-sm border rounded"
                          />
                        </>
                      ) : (
                        `¥${receipt.tax?.toLocaleString() || '0'}`
                      )}
                    </div>
                  </div>
                  
                  {/* 修正履歴 */}
                  {showHistory === receipt.id && receipt.history && receipt.history.length > 0 && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                      <h4 className="text-xs font-semibold text-gray-700 mb-2">修正履歴</h4>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {receipt.history.map((h: any) => (
                          <div key={h.id} className="text-xs text-gray-600">
                            <span className="font-medium">{h.field_name}:</span>{' '}
                            <span className="line-through text-gray-400">{h.old_value || '(空)'}</span>
                            {' → '}
                            <span className="text-gray-800">{h.new_value || '(空)'}</span>
                            <span className="text-gray-400 ml-2">
                              ({format(new Date(h.changed_at), 'MM/dd HH:mm')})
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">領収書データがありません</p>
          )}
        </div>
      </div>

      {/* 仕訳テーブル */}
      <div className="card mt-6">
        <h2 className="text-xl font-semibold mb-4">仕訳候補</h2>
        {journals && journals.length > 0 ? (
          <JournalTable
            journals={journals}
            onRowClick={handleJournalClick}
            onConfirm={handleConfirm}
            onReject={handleReject}
            onUpdate={handleUpdate}
            selectedId={selectedJournal?.id}
          />
        ) : (
          <p className="text-gray-500">仕訳データがありません</p>
        )}
      </div>
    </div>
  )
}