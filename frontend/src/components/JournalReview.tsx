'use client'

import { useState, useRef, useEffect } from 'react'
import { useVideoDetail } from '@/hooks/useVideoDetail'
import { useJournals } from '@/hooks/useJournals'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import JournalTable from './JournalTable'
import ReceiptJournalModal from './ReceiptJournalModal'
import CustomVideoPlayer from './CustomVideoPlayer'
import { ArrowDownTrayIcon, CameraIcon, PlusIcon, XMarkIcon, PencilIcon, CheckIcon, XCircleIcon, ClockIcon, ChevronDownIcon, PlayIcon, PauseIcon, ChevronLeftIcon, ChevronRightIcon, BackwardIcon, ForwardIcon, TrashIcon } from '@heroicons/react/24/outline'

interface JournalReviewProps {
  videoId: number
}

export default function JournalReview({ videoId }: JournalReviewProps) {
  const { data: video, isLoading: videoLoading, refetch: refetchVideo } = useVideoDetail(videoId)
  const { data: journals, isLoading: journalsLoading, refetch: refetchJournals } = useJournals(videoId)
  const [selectedJournal, setSelectedJournal] = useState<any>(null)
  const [selectedReceipt, setSelectedReceipt] = useState<any>(null)
  const [playerReady, setPlayerReady] = useState(false)
  const [playing, setPlaying] = useState(false)  // デフォルトをfalseに（一時停止から開始）
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [videoDuration, setVideoDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [hoveredReceiptId, setHoveredReceiptId] = useState<number | null>(null)
  const [editingReceiptId, setEditingReceiptId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<any>({})
  const [showHistory, setShowHistory] = useState<number | null>(null)
  const [exportFormat, setExportFormat] = useState<string>('standard')
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [showReceiptModal, setShowReceiptModal] = useState(false)
  const [modalReceipt, setModalReceipt] = useState<any>(null)
  const [modalJournal, setModalJournal] = useState<any>(null)
  const playerRef = useRef<ReactPlayer>(null)
  const exportMenuRef = useRef<HTMLDivElement>(null)

  // Close export menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setShowExportMenu(false)
      }
    }

    if (showExportMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showExportMenu])

  const handleJournalClick = (journal: any) => {
    setSelectedJournal(journal)
    
    // 該当する領収書を検索
    const relatedReceipt = video.receipts?.find((r: any) => r.id === journal.receipt_id)
    
    if (relatedReceipt) {
      // 領収書も選択
      setSelectedReceipt(relatedReceipt)
      
      // ビデオシーク
      if (relatedReceipt.best_frame?.time_ms !== undefined && playerRef.current && playerReady) {
        const seconds = relatedReceipt.best_frame.time_ms / 1000
        setPlaying(false)
        
        setTimeout(() => {
          if (playerRef.current) {
            playerRef.current.seekTo(seconds, 'seconds')
          }
        }, 100)
      }
      
      // モーダルを開く（オプション）
      setModalReceipt(relatedReceipt)
      setModalJournal(journal)
      setShowReceiptModal(true)
    } else if (playerRef.current && journal.time_ms) {
      // フォールバック: journalのtime_msを使用
      const seconds = journal.time_ms / 1000
      playerRef.current.seekTo(seconds)
    }
  }

  const handleReceiptClick = (receipt: any) => {
    console.log('Receipt clicked:', receipt)
    setSelectedReceipt(receipt)
    
    // ビデオシーク
    if (receipt.best_frame?.time_ms !== undefined && receipt.best_frame.time_ms !== null) {
      const seconds = receipt.best_frame.time_ms / 1000
      console.log('Attempting to seek to:', seconds, 'seconds')
      
      if (playerRef.current && playerReady) {
        // 再生停止
        setPlaying(false)
        
        // 少し遅延後にシーク（Reactステート更新待機）
        setTimeout(() => {
          if (playerRef.current) {
            try {
              // ReactPlayerのseekToメソッドを直接呼び出し
              playerRef.current.seekTo(seconds, 'seconds')
              console.log('Seeked using ReactPlayer seekTo')
              
              // 追加で内部プレーヤーへのアクセスを試行
              setTimeout(() => {
                try {
                  const internalPlayer = playerRef.current?.getInternalPlayer()
                  if (internalPlayer && typeof internalPlayer.currentTime !== 'undefined') {
                    internalPlayer.currentTime = seconds
                    console.log('Also set currentTime directly:', seconds)
                  }
                } catch (e) {
                  console.log('Could not access internal player:', e)
                }
              }, 100)
            } catch (e) {
              console.error('Seek error:', e)
            }
          }
        }, 100)
      } else {
        console.log('Player not ready or ref is null')
      }
    } else {
      console.log('No valid time_ms in best_frame')
    }
    
    // 該当する領収書の仕訳データを検索
    const relatedJournal = journals?.find((j: any) => j.receipt_id === receipt.id)
    
    // モーダルを開く
    setModalReceipt(receipt)
    setModalJournal(relatedJournal)
    setShowReceiptModal(true)
  }

  const handleFrameStep = (direction: 'forward' | 'backward') => {
    if (playerRef.current && playerReady) {
      const currentSeconds = playerRef.current.getCurrentTime()
      const frameRate = 30 // 一般的なフレームレート（調整可能）
      const frameDuration = 1 / frameRate
      const newTime = direction === 'forward' 
        ? currentSeconds + frameDuration
        : Math.max(0, currentSeconds - frameDuration)
      
      setPlaying(false)
      playerRef.current.seekTo(newTime, 'seconds')
      console.log(`Frame ${direction}: ${currentSeconds} -> ${newTime}`)
    }
  }

  const handleSecondsJump = (seconds: number) => {
    if (playerRef.current && playerReady) {
      const currentSeconds = playerRef.current.getCurrentTime()
      const newTime = Math.max(0, currentSeconds + seconds)
      
      playerRef.current.seekTo(newTime, 'seconds')
      console.log(`Jump ${seconds}s: ${currentSeconds} -> ${newTime}`)
    }
  }

  const handlePlayerReady = () => {
    setPlayerReady(true)
    if (playerRef.current) {
      setVideoDuration(playerRef.current.getDuration())
    }
  }

  const handleProgress = (state: { played: number; playedSeconds: number }) => {
    setCurrentTime(state.playedSeconds)
  }

  const handleDuration = (duration: number) => {
    setVideoDuration(duration)
  }

  const handleMarkerClick = (timeMs: number) => {
    if (playerRef.current && playerReady) {
      const seconds = timeMs / 1000
      setPlaying(false)
      requestAnimationFrame(() => {
        if (playerRef.current) {
          try {
            const player = playerRef.current.getInternalPlayer()
            if (player && player.currentTime !== undefined) {
              player.currentTime = seconds
            } else {
              playerRef.current.seekTo(seconds)
            }
          } catch (e) {
            playerRef.current.seekTo(seconds)
          }
        }
      })
    }
  }

  const handleAnalyzeCurrentFrame = async () => {
    if (!playerRef.current || !playerReady) {
      toast.error('動画プレイヤーが準備できていません')
      return
    }

    try {
      setIsAnalyzing(true)
      
      // 再生中ならまず一時停止
      if (playing) {
        setPlaying(false)
        // 一時停止が適用されるまで少し待機
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      
      // 一時停止後の正確な現在時間を取得
      const currentTime = playerRef.current.getCurrentTime()
      const timeMs = Math.round(currentTime * 1000)  // Math.floorの代わりにMath.roundを使用
      
      console.log('Analyzing frame at:', currentTime, 'seconds (', timeMs, 'ms)')
      console.log('Player internal time:', playerRef.current.getInternalPlayer()?.currentTime)
      
      const response = await api.post(`/api/videos/${videoId}/analyze-frame`, null, {
        params: { time_ms: timeMs }
      })
      
      console.log('Frame analysis response:', response.data)
      
      if (response.data.receipt_id) {
        toast.success(`フレーム分析完了: ${Math.floor(timeMs/1000)}秒地点`)
        // ページリロードの代わりにデータのみリフェッチ
        setTimeout(() => {
          window.location.reload()
        }, 1000)
      } else {
        toast.warning('この位置に領収書データが見つかりませんでした')
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
      
      await api.patch(`/api/videos/${videoId}/receipts/${receiptId}`, updateData)
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
        const response = await api.get(`/api/videos/${videoId}/receipts/${receiptId}/history`)
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
      await api.delete(`/api/videos/${videoId}/receipts/${receiptId}`)
      toast.success('領収書を削除しました')
      window.location.reload()
    } catch (error: any) {
      console.error('Delete receipt error:', error)
      toast.error(error.response?.data?.detail || '削除に失敗しました')
    }
  }

  const handleConfirm = async (journalId: number) => {
    try {
      await api.post(`/api/journals/${journalId}/confirm`, {
        confirmed_by: 'user'
      })
      toast.success('仕訳を確認しました')
      refetchJournals()
    } catch (error) {
      toast.error('確認に失敗しました')
    }
  }

  const handleReject = async (journalId: number) => {
    try {
      await api.post(`/api/journals/${journalId}/reject`)
      toast.success('仕訳を差戻しました')
      refetchJournals()
    } catch (error) {
      toast.error('差戻しに失敗しました')
    }
  }

  const handleUpdate = async (journalId: number, data: any) => {
    try {
      await api.patch(`/api/journals/${journalId}`, data)
      toast.success('仕訳を更新しました')
      refetchJournals()
    } catch (error) {
      toast.error('更新に失敗しました')
    }
  }

  const handleExportCSV = async (format: string = 'standard') => {
    try {
      const response = await api.get(`/api/export/csv?video_id=${videoId}&format=${format}`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      
      // Format specific file naming
      const formatSuffix = format !== 'standard' ? `_${format}` : ''
      link.setAttribute('download', `journal_export${formatSuffix}_${videoId}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      
      const formatNames: { [key: string]: string } = {
        'standard': '標準形式',
        'yayoi': '弥生会計',
        'freee': 'freee',
        'moneyforward': 'MoneyForward'
      }
      
      toast.success(`${formatNames[format] || format}形式でCSVをダウンロードしました`)
      setShowExportMenu(false)
    } catch (error) {
      toast.error('エクスポートに失敗しました')
    }
  }

  const exportFormats = [
    { value: 'standard', label: '標準形式', description: 'シンプルな汎用形式' },
    { value: 'yayoi', label: '弥生会計', description: '弥生会計インポート対応' },
    { value: 'freee', label: 'freee', description: 'クラウド会計freee対応' },
    { value: 'moneyforward', label: 'MoneyForward', description: 'マネーフォワード対応' }
  ]

  if (videoLoading || journalsLoading) {
    return <div className="card">読み込み中...</div>
  }

  if (!video) {
    return <div className="card">動画が見つかりません</div>
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ヘッダー */}
      <div className="bg-white shadow-sm border-b sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">領収書分析レビュー</h1>
            <div className="relative" ref={exportMenuRef}>
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                className="btn-primary flex items-center"
              >
                <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
                CSV出力
                <ChevronDownIcon className={`h-4 w-4 ml-2 transition-transform ${showExportMenu ? 'rotate-180' : ''}`} />
              </button>
              
              {showExportMenu && (
                <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                  <div className="py-2">
                    {exportFormats.map((format) => (
                      <button
                        key={format.value}
                        onClick={() => handleExportCSV(format.value)}
                        className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
                      >
                        <div className="font-medium text-gray-900">{format.label}</div>
                        <div className="text-xs text-gray-500 mt-1">{format.description}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* メインコンテンツ */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* 左側: ビデオプレイヤー (8列) */}
          <div className="col-span-8">
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="p-4 border-b bg-gray-50">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">動画プレイヤー</h2>
                  <div className="flex items-center gap-2">
                    {/* 現在時間表示 */}
                    <div className="text-sm text-gray-600 px-2">
                      {Math.floor(currentTime)}s / {Math.floor(videoDuration)}s
                    </div>
                    
                    {/* 分析ボタン */}
                    <button
                      onClick={handleAnalyzeCurrentFrame}
                      disabled={isAnalyzing || !playerReady}
                      className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isAnalyzing || !playerReady
                          ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
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
                          現在フレーム分析
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="relative w-full" style={{ aspectRatio: '16/9' }}>
                <CustomVideoPlayer
                  url={video.local_path ? `http://localhost:5001/${video.local_path}` : ''}
                  receipts={video.receipts || []}
                  onReceiptClick={handleReceiptClick}
                  onTimeUpdate={(time) => setCurrentTime(time)}
                  onDuration={(duration) => setVideoDuration(duration)}
                />
              </div>
              
            </div>
          </div>

          {/* 右側: 領収書リスト (4列) */}
          <div className="col-span-4">
            <div className="bg-white rounded-lg shadow-md overflow-hidden" style={{ maxHeight: '600px' }}>
              <div className="p-4 border-b bg-gray-50">
                <h2 className="text-lg font-semibold">領収書一覧 ({video.receipts?.length || 0}件)</h2>
              </div>
              
              <div className="overflow-y-auto" style={{ maxHeight: '540px' }}>
                {video.receipts && video.receipts.length > 0 ? (
                  <div className="divide-y divide-gray-200">
                    {[...video.receipts]
                      .sort((a, b) => {
                        const timeA = a.best_frame?.time_ms || 0
                        const timeB = b.best_frame?.time_ms || 0
                        return timeA - timeB
                      })
                      .map((receipt: any, index: number) => {
        // この領収書のjournalを検索
                        const relatedJournal = journals?.find((j: any) => j.receipt_id === receipt.id)
                        const isJournalConfirmed = relatedJournal?.status === 'confirmed'
                        
                        return (
                          <div 
                            key={receipt.id} 
                            className={`p-3 cursor-pointer transition-all hover:bg-gray-50 ${
                              selectedReceipt?.id === receipt.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                            }`}
                            onClick={() => handleReceiptClick(receipt)}
                          >
                            <div className="flex items-start gap-3">
                              {/* 番号とサムネイル */}
                              <div className="flex-shrink-0">
                                <div className="relative">
                                  <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-xs font-bold text-gray-700">
                                    {index + 1}
                                  </div>
                                  {/* 確認状態バッジ */}
                                  {isJournalConfirmed && (
                                    <CheckIcon className="absolute -right-1 -bottom-1 h-4 w-4 text-white bg-green-600 rounded-full p-0.5" />
                                  )}
                                </div>
                            {receipt.best_frame && (
                              <img 
                                src={`http://localhost:5001/api/videos/frames/${receipt.best_frame.id}/image`}
                                alt="Receipt"
                                className="w-16 h-12 object-cover rounded mt-2 border"
                              />
                            )}
                          </div>
                          
                          {/* 情報 */}
                          <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {receipt.vendor || '不明な店舗'}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {receipt.best_frame && `${(receipt.best_frame.time_ms / 1000).toFixed(1)}秒`}
                                  {receipt.is_manual && ' (手動)'}
                                </p>
                              </div>
                              {/* 削除ボタン */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteReceipt(receipt.id, e);
                                }}
                                className="p-1 hover:bg-red-100 rounded transition-colors group"
                                title="領収書を削除"
                              >
                                <TrashIcon className="h-4 w-4 text-gray-400 group-hover:text-red-600" />
                              </button>
                            </div>
                            
                            <div className="mt-2 grid grid-cols-2 gap-1 text-xs">
                              <div>
                                <span className="text-gray-500">金額:</span>
                                <span className="ml-1 font-medium">¥{receipt.total?.toLocaleString() || '0'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">税額:</span>
                                <span className="ml-1">¥{receipt.tax?.toLocaleString() || '0'}</span>
                              </div>
                              <div className="col-span-2">
                                <span className="text-gray-500">日付:</span>
                                <span className="ml-1">
                                  {receipt.issue_date
                                    ? format(new Date(receipt.issue_date), 'yyyy/MM/dd', { locale: ja })
                                    : '-'}
                                </span>
                              </div>
                            </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    領収書データがありません
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 仕訳テーブル */}
        <div className="mt-6 bg-white rounded-lg shadow-md p-6">
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
            <p className="text-gray-500 text-center py-8">仕訳データがありません</p>
          )}
        </div>
      </div>

      {/* 領収書と仕訳の詳細モーダル */}
      <ReceiptJournalModal
        receipt={modalReceipt}
        journal={modalJournal}
        allJournals={journals || []}
        videoId={videoId}
        videoDuration={videoDuration}
        isOpen={showReceiptModal}
        onClose={() => {
          setShowReceiptModal(false)
          setModalReceipt(null)
          setModalJournal(null)
        }}
        onUpdate={async () => {
          // データ再取得 (リロードではなくrefetch)
          await Promise.all([
            refetchVideo(),
            refetchJournals()
          ])
        }}
        allReceipts={video?.receipts || []}
        onReceiptChange={(receiptId: number) => {
          // 新しい領収書に切り替え
          const newReceipt = video?.receipts?.find((r: any) => r.id === receiptId)
          if (newReceipt) {
            setModalReceipt(newReceipt)
            // 関連する仕訳も更新
            const relatedJournal = journals?.find((j: any) => j.receipt_id === receiptId)
            setModalJournal(relatedJournal || null)
          }
        }}
      />

    </div>
  )
}