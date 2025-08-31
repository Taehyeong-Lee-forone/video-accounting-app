'use client'

import { useState, useRef, useEffect } from 'react'
import { useVideoDetail } from '@/hooks/useVideoDetail'
import { useJournals } from '@/hooks/useJournals'
import { api, API_URL } from '@/lib/api'
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
  const [videoReady, setVideoReady] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const exportMenuRef = useRef<HTMLDivElement>(null)

  // ビデオ要素の準備状態を監視
  useEffect(() => {
    const checkVideoReady = () => {
      const video = videoRef.current
      if (video && video.readyState >= 2) {
        setVideoReady(true)
      }
    }

    // 定期的にチェック
    const interval = setInterval(checkVideoReady, 100)
    
    // イベントリスナーも追加
    const video = videoRef.current
    if (video) {
      const handleCanPlay = () => setVideoReady(true)
      video.addEventListener('canplay', handleCanPlay)
      
      return () => {
        clearInterval(interval)
        video.removeEventListener('canplay', handleCanPlay)
      }
    }
    
    return () => clearInterval(interval)
  }, [video?.local_path]) // ビデオパスが変更されたら再実行

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
      if (relatedReceipt.best_frame?.time_ms !== undefined && videoRef.current) {
        const seconds = relatedReceipt.best_frame.time_ms / 1000
        setPlaying(false)
        
        setTimeout(() => {
          if (videoRef.current) {
            videoRef.current.currentTime = seconds
          }
        }, 100)
      }
      
      // モーダルを開く（オプション）
      setModalReceipt(relatedReceipt)
      setModalJournal(journal)
      setShowReceiptModal(true)
    } else if (videoRef.current && journal.time_ms) {
      // フォールバック: journalのtime_msを使用
      const seconds = journal.time_ms / 1000
      videoRef.current.currentTime = seconds
    }
  }

  const handleReceiptClick = (receipt: any) => {
    // 領収書が有効かチェック
    if (!receipt || !receipt.id) {
      toast.error('領収書データが無効です')
      return
    }
    
    setSelectedReceipt(receipt)
    
    // ビデオシーク
    if (receipt.best_frame?.time_ms !== undefined && receipt.best_frame.time_ms !== null) {
      const seconds = receipt.best_frame.time_ms / 1000
      
      const performSeek = () => {
        if (!videoRef.current) {
          toast.error('ビデオプレーヤーが準備できていません')
          return
        }
        
        const video = videoRef.current
        
        // ビデオが準備完了しているかチェック
        if (!videoReady || video.readyState < 2) {
          // まだ準備できていない場合は待機
          const checkInterval = setInterval(() => {
            if (video.readyState >= 2) {
              clearInterval(checkInterval)
              video.pause()
              setPlaying(false)
              try {
                video.currentTime = seconds
              } catch (e) {
                toast.error('シーク中にエラーが発生しました')
              }
            }
          }, 100)
          
          // タイムアウト設定（3秒）
          setTimeout(() => {
            clearInterval(checkInterval)
            if (video.readyState < 2) {
              toast.error('ビデオの読み込みに失敗しました')
            }
          }, 3000)
        } else {
          // 準備完了している場合は即座にシーク
          video.pause()
          setPlaying(false)
          
          try {
            video.currentTime = seconds
          } catch (e) {
            toast.error('シーク中にエラーが発生しました')
          }
        }
      }
      
      // 即座に実行を試みる
      performSeek()
    } else {
      // time_msがない場合も選択状態にはする
      toast('この領収書にはタイムスタンプがありません')
    }
    
    // 領収書クリック時にモーダルは開かない（ビデオシークのみ実行）
  }
  
  // 새로운 함수: 상세보기 모달 열기
  const handleOpenReceiptModal = (receipt: any) => {
    // 該当する領収書の仕訳データを検索
    const relatedJournal = journals?.find((j: any) => j.receipt_id === receipt.id)
    
    // モーダルを開く
    setModalReceipt(receipt)
    setModalJournal(relatedJournal)
    setShowReceiptModal(true)
  }

  const handleFrameStep = (direction: 'forward' | 'backward') => {
    if (videoRef.current) {
      const currentSeconds = videoRef.current.currentTime
      const frameRate = 30 // 一般的なフレームレート（調整可能）
      const frameDuration = 1 / frameRate
      const newTime = direction === 'forward' 
        ? currentSeconds + frameDuration
        : Math.max(0, currentSeconds - frameDuration)
      
      setPlaying(false)
      videoRef.current.currentTime = newTime
      console.log(`Frame ${direction}: ${currentSeconds} -> ${newTime}`)
    }
  }

  const handleSecondsJump = (seconds: number) => {
    if (videoRef.current) {
      const currentSeconds = videoRef.current.currentTime
      const newTime = Math.max(0, currentSeconds + seconds)
      
      videoRef.current.currentTime = newTime
      console.log(`Jump ${seconds}s: ${currentSeconds} -> ${newTime}`)
    }
  }

  const handlePlayerReady = () => {
    setPlayerReady(true)
    if (videoRef.current) {
      setVideoDuration(videoRef.current.duration)
    }
  }

  const handleProgress = (state: { played: number; playedSeconds: number }) => {
    setCurrentTime(state.playedSeconds)
  }

  const handleDuration = (duration: number) => {
    setVideoDuration(duration)
  }

  const handleMarkerClick = (timeMs: number) => {
    if (videoRef.current) {
      const seconds = timeMs / 1000
      setPlaying(false)
      requestAnimationFrame(() => {
        if (videoRef.current) {
          try {
            videoRef.current.currentTime = seconds
          } catch (e) {
            console.error('Seek error:', e)
          }
        }
      })
    }
  }

  const handleAnalyzeCurrentFrame = async () => {
    if (!videoRef.current) {
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
      const currentTime = videoRef.current.currentTime
      const timeMs = Math.round(currentTime * 1000)  // Math.floorの代わりにMath.roundを使用
      
      console.log('Analyzing frame at:', currentTime, 'seconds (', timeMs, 'ms)')
      console.log('Video currentTime:', videoRef.current.currentTime)
      
      const response = await api.post(`/videos/${videoId}/analyze-frame`, null, {
        params: { time_ms: timeMs }
      })
      
      console.log('Frame analysis response:', response.data)
      
      if (response.data.receipt_id) {
        toast.success(`フレーム分析完了: ${Math.floor(timeMs/1000)}秒地点`)
        // データのみリフェッチして即座に反映
        await Promise.all([
          refetchVideo(),
          refetchJournals()
        ])
      } else {
        toast('この位置に領収書データが見つかりませんでした')
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
      
      // データの再取得
      await Promise.all([
        refetchVideo(),
        refetchJournals()
      ])
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
      // データの再取得
      await Promise.all([
        refetchVideo(),
        refetchJournals()
      ])
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
      refetchJournals()
    } catch (error) {
      toast.error('確認に失敗しました')
    }
  }

  const handleReject = async (journalId: number) => {
    try {
      await api.post(`/journals/${journalId}/reject`)
      toast.success('仕訳を差戻しました')
      refetchJournals()
    } catch (error) {
      toast.error('差戻しに失敗しました')
    }
  }

  const handleUpdate = async (journalId: number, data: any) => {
    try {
      await api.patch(`/journals/${journalId}`, data)
      toast.success('仕訳を更新しました')
      refetchJournals()
    } catch (error) {
      toast.error('更新に失敗しました')
    }
  }

  const handleExportCSV = async (format: string = 'standard') => {
    try {
      const response = await api.get(`/export/csv?video_id=${videoId}&format=${format}`, {
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
            <div className="flex items-center gap-3">
              {/* 詳細表示ボタン */}
              <button
                onClick={() => {
                  if (selectedReceipt) {
                    handleOpenReceiptModal(selectedReceipt)
                  } else {
                    alert('領収書を選択してください')
                  }
                }}
                className="btn-secondary flex items-center"
                disabled={!selectedReceipt}
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                詳細表示
              </button>
              
              {/* CSV出力ボタン */}
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
      </div>

      {/* メインコンテンツ */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* 左側: ビデオプレイヤー (8列) */}
          <div className="col-span-8">
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="p-4 border-b bg-gray-50">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900">動画プレイヤー</h2>
                  <div className="flex items-center gap-2">
                    {/* 現在時間表示 */}
                    <div className="text-sm text-gray-600 px-2">
                      {Math.floor(currentTime)}s / {Math.floor(videoDuration)}s
                    </div>
                    
                    {/* 分析ボタン */}
                    <button
                      onClick={handleAnalyzeCurrentFrame}
                      disabled={isAnalyzing || !videoRef.current}
                      className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isAnalyzing || !videoRef.current
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
                  key={`video-${videoId}-${video.updated_at}`}
                  url={video.local_path ? `${API_URL}/${video.local_path}` : ''}
                  receipts={video.receipts || []}
                  onReceiptClick={handleReceiptClick}
                  onTimeUpdate={(time) => setCurrentTime(time)}
                  onDuration={(duration) => setVideoDuration(duration)}
                  videoRef={videoRef}
                />
              </div>
              
            </div>
          </div>

          {/* 右側: 領収書リスト (4列) */}
          <div className="col-span-4">
            <div className="bg-white rounded-lg shadow-md overflow-hidden" style={{ maxHeight: '600px' }}>
              <div className="p-4 border-b bg-gray-50">
                <h2 className="text-lg font-semibold text-gray-800">領収書一覧 ({video.receipts?.length || 0}件)</h2>
              </div>
              
              <div className="overflow-y-auto" style={{ maxHeight: '540px' }}>
                {video.receipts && video.receipts.length > 0 ? (
                  <div className="divide-y divide-gray-200">
                    {[...video.receipts]
                      .filter((receipt) => receipt && receipt.id) // 有効な領収書のみフィルタリング
                      .sort((a, b) => {
                        const timeA = a?.best_frame?.time_ms || 0
                        const timeB = b?.best_frame?.time_ms || 0
                        return timeA - timeB
                      })
                      .map((receipt: any, index: number) => {
        // この領収書のjournalを検索
                        const relatedJournal = journals?.find((j: any) => j.receipt_id === receipt.id)
                        const isJournalConfirmed = relatedJournal?.status === 'confirmed'
                        
                        return (
                          <div 
                            key={`receipt-${receipt.id}-${index}`} 
                            className={`p-3 cursor-pointer transition-all hover:bg-gray-50 ${
                              selectedReceipt?.id === receipt.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                            }`}
                            onClick={(e) => {
                              // 削除ボタンがクリックされた場合は処理しない
                              if ((e.target as HTMLElement).closest('button')) {
                                return;
                              }
                              console.log('=== Receipt List Item Click ===')
                              console.log('Receipt ID:', receipt?.id)
                              console.log('Receipt vendor:', receipt?.vendor)
                              console.log('Receipt best_frame:', receipt?.best_frame)
                              console.log('Receipt time_ms:', receipt?.best_frame?.time_ms)
                              console.log('Full receipt data:', JSON.stringify(receipt, null, 2))
                              handleReceiptClick(receipt)
                            }}
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
                                src={`${API_URL}/videos/frames/${receipt.best_frame.id}/image`}
                                alt="Receipt"
                                className="w-16 h-12 object-cover rounded mt-2 border"
                                onError={(e) => {
                                  // フレーム画像が見つからない場合はプレースホルダーを表示
                                  e.currentTarget.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNDgiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjQ4IiBmaWxsPSIjZTVlN2ViIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzZiNzI4MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuOBquOBlzwvdGV4dD48L3N2Zz4='
                                }}
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
                                <span className="ml-1 font-medium text-gray-800">¥{receipt.total?.toLocaleString() || '0'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">税額:</span>
                                <span className="ml-1 text-gray-700">¥{receipt.tax?.toLocaleString() || '0'}</span>
                              </div>
                              <div className="col-span-2">
                                <span className="text-gray-500">日付:</span>
                                <span className="ml-1 text-gray-700">
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
          <h2 className="text-xl font-semibold text-gray-900 mb-4">仕訳候補</h2>
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