'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { format } from 'date-fns'
import { ja } from 'date-fns/locale'
import { XMarkIcon, CheckIcon, XCircleIcon, PencilIcon, ChevronLeftIcon, ChevronRightIcon, CameraIcon, PlusIcon, TrashIcon, ClockIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { api, API_URL } from '@/lib/api'

interface ReceiptJournalModalProps {
  receipt: any
  journal: any
  allJournals?: any[]  // すべてのjournalリスト
  videoId: number
  videoDuration?: number
  isOpen: boolean
  onClose: () => void
  onUpdate: () => void
  allReceipts?: any[]  // すべての領収書リスト
  onReceiptChange?: (receiptId: number) => void  // 領収書変更コールバック
}

export default function ReceiptJournalModal({ 
  receipt, 
  journal, 
  allJournals = [],
  videoId,
  videoDuration = 0,
  isOpen, 
  onClose,
  onUpdate,
  allReceipts = [],
  onReceiptChange
}: ReceiptJournalModalProps) {
  // 常に編集モードで開始
  const [receiptForm, setReceiptForm] = useState<any>({})
  const [journalForm, setJournalForm] = useState<any>({})
  const [isSaving, setIsSaving] = useState(false)
  const [isConfirmed, setIsConfirmed] = useState(false)
  const [currentFrameTime, setCurrentFrameTime] = useState<number>(0)
  const [isLoadingFrame, setIsLoadingFrame] = useState(false)
  const hiddenVideoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [videoLoaded, setVideoLoaded] = useState(false)
  const [videoUrl, setVideoUrl] = useState<string>('')
  // 이미지 URL 제거 - 비디오/캔버스만 사용
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [ocrPreviewData, setOcrPreviewData] = useState<any>(null)
  const [showOcrConfirmDialog, setShowOcrConfirmDialog] = useState(false)
  const [showReceiptList, setShowReceiptList] = useState(true)  // 領収書リスト表示状態
  const [ocrApplyMode, setOcrApplyMode] = useState<'overwrite' | 'new'>('overwrite')  // OCR適用モード
  const [localReceipts, setLocalReceipts] = useState(allReceipts)  // ローカル領収書リスト
  const [imageViewMode, setImageViewMode] = useState<'contain' | 'cover'>('contain')  // 画像表示モード
  const [zoomLevel, setZoomLevel] = useState(1)  // ズームレベル
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 })  // 画像位置
  const [isDragging, setIsDragging] = useState(false)  // ドラッグ状態
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })  // ドラッグ開始位置
  const [confirmAnimating, setConfirmAnimating] = useState(false)  // 確認アニメーション状態
  const imageContainerRef = useRef<HTMLDivElement>(null)

  // Receipt IDを追跡して実際に異なる領収書に変更されたときのみリセット
  const [lastReceiptId, setLastReceiptId] = useState<number | null>(null)
  
  // allReceiptsが変更されたかモーダルが開かれたときlocalReceiptsを更新
  useEffect(() => {
    if (isOpen) {
      setLocalReceipts(allReceipts)
    }
  }, [allReceipts, isOpen])
  
  useEffect(() => {
    if (receipt) {
      setReceiptForm({
        vendor: receipt.vendor || '',
        total: receipt.total || 0,
        tax: receipt.tax || 0,
        issue_date: receipt.issue_date ? format(new Date(receipt.issue_date), 'yyyy-MM-dd') : '',
        payment_method: receipt.payment_method || '',
        memo: receipt.memo || ''
      })
      
      // 異なる領収書に変更されたときのみフレーム時間を初期化
      if (receipt.id !== lastReceiptId) {
        setLastReceiptId(receipt.id)
        if (receipt.best_frame?.time_ms !== undefined) {
          setCurrentFrameTime(receipt.best_frame.time_ms)
          // ビデオがロードされていたら、その時間にシーク
          if (hiddenVideoRef.current && videoLoaded) {
            hiddenVideoRef.current.currentTime = receipt.best_frame.time_ms / 1000
            // seekedイベントでキャプチャされるので、ここでは呼ばない
          }
        }
      }
    }
  }, [receipt, lastReceiptId])

  useEffect(() => {
    if (journal) {
      setJournalForm({
        debit_account: journal.debit_account || '',
        credit_account: journal.credit_account || '',
        debit_amount: journal.debit_amount || 0,
        credit_amount: journal.credit_amount || 0,
        tax_account: journal.tax_account || '',
        tax_amount: journal.tax_amount || 0,
        memo: journal.memo || ''
      })
      // journalのstatusが'confirmed'か確認
      setIsConfirmed(journal.status === 'confirmed')
    } else {
      setIsConfirmed(false)
    }
  }, [journal])
  
  // ビデオフレームをcanvasにキャプチャ（最適化版）
  const captureVideoFrame = useCallback(() => {
    if (!hiddenVideoRef.current || !canvasRef.current) {
      console.warn('⚠️ Cannot capture frame: refs not ready')
      return
    }
    
    const video = hiddenVideoRef.current
    const canvas = canvasRef.current
    
    // ビデオが準備できているか確認
    if (video.readyState < 2) {
      console.warn('⚠️ Video not ready for capture, readyState:', video.readyState)
      return
    }
    
    const ctx = canvas.getContext('2d', { alpha: false })
    if (!ctx) return
    
    // canvasサイズを一度だけ設定
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth || 800
      canvas.height = video.videoHeight || 600
    }
    
    // ビデオフレームを即座に描画
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    console.log('📸 Frame captured at', video.currentTime, 'seconds')
  }, [])
  
  // ビデオをロードしてビデオを準備
  useEffect(() => {
    if (isOpen && videoId) {
      console.log('🎬 Loading video for modal, videoId:', videoId)
      setVideoLoaded(false)
      
      // ビデオ情報を取得
      api.get(`/videos/${videoId}`).then(response => {
        const videoPath = response.data.local_path
        const filename = videoPath?.split('/').pop()
        if (filename) {
          const url = `${API_URL}/videos/stream/${filename}`
          console.log('🎬 Video URL:', url)
          setVideoUrl(url)
        }
      }).catch(error => {
        console.error('Failed to get video info:', error)
      })
    }
  }, [isOpen, videoId])
  
  // ビデオURLが設定されたらビデオをロード
  useEffect(() => {
    if (videoUrl && hiddenVideoRef.current) {
      const video = hiddenVideoRef.current
      console.log('🎬 Setting video src:', videoUrl)
      
      // 既に同じURLが設定されている場合はスキップ
      if (video.src === videoUrl) {
        console.log('🎬 Video already loaded with this URL')
        return
      }
      
      video.src = videoUrl
      video.crossOrigin = 'anonymous'
      
      // ビデオが完全にロードされたら（一度だけ実行）
      const handleCanPlayThrough = () => {
        console.log('🎬 Video can play through!')
        setVideoLoaded(true)
        
        // 初期位置にシーク
        if (receipt?.best_frame?.time_ms !== undefined) {
          video.currentTime = receipt.best_frame.time_ms / 1000
        }
      }
      
      // シーク完了時にフレームをキャプチャ
      const handleSeeked = () => {
        console.log('🎬 Seek completed at', video.currentTime)
        captureVideoFrame()
      }
      
      const handleError = (e: Event) => {
        console.error('🎬 Video loading error:', e)
      }
      
      video.addEventListener('canplaythrough', handleCanPlayThrough, { once: true })
      video.addEventListener('seeked', handleSeeked)
      video.addEventListener('error', handleError)
      
      video.load()
      
      // クリーンアップ
      return () => {
        video.removeEventListener('canplaythrough', handleCanPlayThrough)
        video.removeEventListener('seeked', handleSeeked)
        video.removeEventListener('error', handleError)
      }
    }
  }, [videoUrl, captureVideoFrame])

  // フレームナビゲーション関数（ビデオ直接制御版）
  const handleFrameNavigation = (direction: 'prev' | 'next', stepSize: 'frame' | 'second' | 'halfSecond' = 'frame') => {
    if (!hiddenVideoRef.current || !videoLoaded) {
      console.warn('⚠️ Video not ready:', { videoRef: !!hiddenVideoRef.current, videoLoaded })
      return
    }
    
    const video = hiddenVideoRef.current
    
    // 移動単位設定（秒単位）
    const step = stepSize === 'frame' 
      ? 0.033  // 30fps基準で1フレーム（約33ms）
      : stepSize === 'halfSecond'
      ? 0.5    // 0.5秒
      : 1.0    // 1秒
    
    const newTime = direction === 'next' 
      ? Math.min(video.duration || Infinity, video.currentTime + step)
      : Math.max(0, video.currentTime - step)
    
    console.log(`🎬 Seeking from ${video.currentTime}s to ${newTime}s`)
    
    // ビデオの再生位置を変更
    video.currentTime = newTime
    setCurrentFrameTime(Math.round(newTime * 1000))
    
    // seekedイベントでキャプチャされるので、ここでは即座にキャプチャを試みる
    // ビデオがすでにその位置にある場合のため
    if (Math.abs(video.currentTime - newTime) < 0.001) {
      requestAnimationFrame(() => {
        captureVideoFrame()
      })
    }
    
    const stepLabel = stepSize === 'frame' ? 'フレーム' : '秒'
    console.log(`${direction === 'next' ? '次' : '前'}の${stepLabel}: ${newTime}s`)
  }

  // 現在フレームでOCR再分析（プレビュー）
  const handleReanalyzeFrame = async () => {
    if (!videoId || !currentFrameTime) {
      toast.error('フレーム情報が不足しています')
      return
    }

    setIsAnalyzing(true)
    try {
      // フレーム分析プレビューAPI呼び出し（保存しない）
      const response = await api.post(`/videos/${videoId}/analyze-frame-preview`, null, {
        params: { time_ms: currentFrameTime }
      })
      
      if (response.data.success && response.data.receipt_data) {
        // OCR成功 - 選択されたモードに応じて即座に適用
        setOcrPreviewData(response.data.receipt_data)
        
        if (ocrApplyMode === 'overwrite') {
          // 現在の領収書を上書き
          await handleApplyOcrDataDirect(response.data.receipt_data)
        } else {
          // 新しい領収書を作成
          await handleCreateNewReceiptDirect(response.data.receipt_data)
        }
      } else {
        toast('領収書データが検出されませんでした')
      }
    } catch (error: any) {
      console.error('OCR preview error:', error)
      toast.error(error.response?.data?.detail || 'OCR分析に失敗しました')
    } finally {
      setIsAnalyzing(false)
    }
  }

  // OCRデータ直接適用（ダイアログなし）
  const handleApplyOcrDataDirect = async (data: any) => {
    if (data && receipt) {
      // OCRデータをフォームに適用
      setReceiptForm({
        vendor: data.vendor || '',
        total: data.total || 0,
        tax: data.tax || 0,
        issue_date: data.issue_date ? 
          (typeof data.issue_date === 'string' && data.issue_date.includes('-') 
            ? data.issue_date.split('T')[0]
            : format(new Date(data.issue_date), 'yyyy-MM-dd'))
          : '',
        payment_method: data.payment_method || '',
        memo: data.memo || ''
      })
      
      // フレームも更新（現在表示中のフレームへ）
      try {
        const response = await api.post(
          `/videos/${videoId}/receipts/${receipt.id}/update-frame`,
          null,
          { params: { time_ms: currentFrameTime } }
        )
        
        if (response.data.success) {
          // ビデオシーク位置を更新
          const newTime = response.data.time_ms || currentFrameTime
          if (hiddenVideoRef.current && videoLoaded) {
            hiddenVideoRef.current.currentTime = newTime / 1000
            // seekedイベントでキャプチャされる
          }
          
          // receiptオブジェクトも更新（新しいフレーム情報で）
          if (receipt.best_frame) {
            receipt.best_frame.id = response.data.new_frame_id
            receipt.best_frame.time_ms = newTime
          }
          
          // 現在フレーム時間も更新
          setCurrentFrameTime(newTime)
          setIsLoadingFrame(false)
          
          toast.success('OCRデータとフレームを適用しました')
        } else {
          toast.success('OCRデータを適用しました')
        }
      } catch (error) {
        console.error('Frame update error:', error)
        toast.success('OCRデータを適用しました')
      }
    }
  }

  // OCRデータ適用（ダイアログから呼び出し）
  const handleApplyOcrData = async () => {
    if (ocrPreviewData && receipt) {
      // OCRデータをフォームに適用
      setReceiptForm({
        vendor: ocrPreviewData.vendor || '',
        total: ocrPreviewData.total || 0,
        tax: ocrPreviewData.tax || 0,
        issue_date: ocrPreviewData.issue_date ? 
          (typeof ocrPreviewData.issue_date === 'string' && ocrPreviewData.issue_date.includes('-') 
            ? ocrPreviewData.issue_date.split('T')[0]
            : format(new Date(ocrPreviewData.issue_date), 'yyyy-MM-dd'))
          : '',
        payment_method: ocrPreviewData.payment_method || '',
        memo: ocrPreviewData.memo || ''
      })
      
      // フレームも更新（現在表示中のフレームへ）
      try {
        const response = await api.post(
          `/videos/${videoId}/receipts/${receipt.id}/update-frame`,
          null,
          { params: { time_ms: currentFrameTime } }
        )
        
        if (response.data.success) {
          // ビデオシーク位置を更新
          const newTime = response.data.time_ms || currentFrameTime
          if (hiddenVideoRef.current && videoLoaded) {
            hiddenVideoRef.current.currentTime = newTime / 1000
            // seekedイベントでキャプチャされる
          }
          
          // receiptオブジェクトも更新（新しいフレーム情報で）
          if (receipt.best_frame) {
            receipt.best_frame.id = response.data.new_frame_id
            receipt.best_frame.time_ms = newTime
          }
          
          // 現在フレーム時間も更新
          setCurrentFrameTime(newTime)
          setIsLoadingFrame(false)
          
          toast.success('OCRデータとフレームを適用しました')
        } else {
          toast.success('OCRデータを適用しました')
        }
      } catch (error) {
        console.error('Frame update error:', error)
        toast.success('OCRデータを適用しました')
      }
      
      setShowOcrConfirmDialog(false)
      setOcrPreviewData(null)
    }
  }

  // 新しい領収書として直接作成（ダイアログなし）
  const handleCreateNewReceiptDirect = async (data: any) => {
    if (data) {
      try {
        // 新しい領収書作成API呼び出し
        const response = await api.post(
          `/videos/${videoId}/analyze-frame`,
          null,
          { params: { time_ms: currentFrameTime } }
        )
        
        if (response.data.receipt_id) {
          toast.success('新しい領収書を作成しました')
          
          // 新しく作成された領収書情報を構成
          const newReceipt = response.data.receipt || {
            id: response.data.receipt_id,
            vendor: data.vendor || '',
            total: data.total || 0,
            tax: data.tax || 0,
            issue_date: data.issue_date,
            payment_method: data.payment_method || '',
            memo: data.memo || '',
            is_manual: true,
            best_frame: {
              id: response.data.frame_id,
              time_ms: response.data.time_ms || currentFrameTime
            },
            best_frame_id: response.data.frame_id
          }
          
          // localReceipts配列に新しい領収書を追加
          const updatedReceipts = [...localReceipts, newReceipt]
          // 時間順にソート
          updatedReceipts.sort((a, b) => {
            const timeA = a.best_frame?.time_ms || 0
            const timeB = b.best_frame?.time_ms || 0
            return timeA - timeB
          })
          
          // ローカル状態を更新
          setLocalReceipts(updatedReceipts)
          
          // 親コンポーネントに更新を通知
          if (onUpdate) {
            // 非同期で実行してUI更新が先に起こるように
            setTimeout(() => {
              onUpdate()
            }, 100)
          }
          
          // 新しく作成された領収書に移動（モーダルは開いた状態を維持）
          if (onReceiptChange && response.data.receipt_id) {
            // 新しい領収書のフレーム時間設定
            setCurrentFrameTime(currentFrameTime)
            // 少し遅延後に新しい領収書に切り替え
            setTimeout(() => {
              onReceiptChange(response.data.receipt_id)
            }, 100)
          }
        } else {
          toast.error('領収書の作成に失敗しました')
        }
      } catch (error) {
        console.error('Create new receipt error:', error)
        toast.error('領収書の作成に失敗しました')
      }
    }
  }

  // 新しい領収書として作成（ダイアログから呼び出し）
  const handleCreateNewReceipt = async () => {
    if (ocrPreviewData) {
      try {
        // 新しい領収書作成API呼び出し
        const response = await api.post(
          `/videos/${videoId}/analyze-frame`,
          null,
          { params: { time_ms: currentFrameTime } }
        )
        
        if (response.data.receipt_id) {
          toast.success('新しい領収書を作成しました')
          
          // ダイアログだけ閉じてモーダルは維持
          setShowOcrConfirmDialog(false)
          setOcrPreviewData(null)
          
          // 新しく作成された領収書に移動（モーダルは開いた状態を維持）
          if (onReceiptChange && response.data.receipt_id) {
            onReceiptChange(response.data.receipt_id)
          }
        } else {
          toast.error('領収書の作成に失敗しました')
        }
      } catch (error) {
        console.error('Create new receipt error:', error)
        toast.error('領収書の作成に失敗しました')
      }
      
      setShowOcrConfirmDialog(false)
      setOcrPreviewData(null)
    }
  }

  // OCRデータキャンセル
  const handleCancelOcrData = () => {
    setShowOcrConfirmDialog(false)
    setOcrPreviewData(null)
  }

  // 他の領収書に切り替え
  const handleReceiptNavigation = (targetReceiptId: number) => {
    // 領収書切り替え時に該当領収書のフレーム時間へリセット
    const targetReceipt = localReceipts.find(r => r.id === targetReceiptId)
    if (targetReceipt?.best_frame) {
      setCurrentFrameTime(targetReceipt.best_frame.time_ms)
      // ビデオシーク
      if (hiddenVideoRef.current && videoLoaded) {
        hiddenVideoRef.current.currentTime = targetReceipt.best_frame.time_ms / 1000
        // seekedイベントでキャプチャされる
      }
    }
    
    if (onReceiptChange) {
      onReceiptChange(targetReceiptId)
    }
  }

  // 現在の領収書のインデックスを検索
  const currentReceiptIndex = localReceipts.findIndex(r => r.id === receipt?.id)
  
  // 前/次の領収書に移動
  const handlePrevReceipt = () => {
    if (currentReceiptIndex > 0 && onReceiptChange) {
      onReceiptChange(localReceipts[currentReceiptIndex - 1].id)
    }
  }
  
  const handleNextReceipt = () => {
    if (currentReceiptIndex < localReceipts.length - 1 && onReceiptChange) {
      onReceiptChange(localReceipts[currentReceiptIndex + 1].id)
    }
  }

  const handleSaveAll = async () => {
    setIsSaving(true)
    try {
      // 領収書データ保存
      const receiptData = {
        ...receiptForm,
        issue_date: receiptForm.issue_date ? new Date(receiptForm.issue_date).toISOString() : null,
        total: parseFloat(receiptForm.total) || 0,
        tax: parseFloat(receiptForm.tax) || 0
      }
      
      await api.patch(`/videos/${videoId}/receipts/${receipt.id}`, receiptData)
      
      // 仕訳データ保存
      if (journal) {
        await api.patch(`/journals/${journal.id}`, journalForm)
      }
      
      toast.success('保存しました')
      onUpdate()
      onClose()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || '保存に失敗しました')
    } finally {
      setIsSaving(false)
    }
  }

  const handleToggleConfirm = async () => {
    if (!journal) {
      toast('仕訳データがありません')
      return
    }
    
    try {
      if (isConfirmed) {
        // 確認を取り消す
        await api.post(`/journals/${journal.id}/reject`)
        setIsConfirmed(false)
        // 取り消し時はアニメーションなし
      } else {
        // 確認する
        await api.post(`/journals/${journal.id}/confirm`, {
          confirmed_by: 'user'
        })
        setIsConfirmed(true)
        // 確認時のみアニメーション効果を発動
        setConfirmAnimating(true)
        setTimeout(() => setConfirmAnimating(false), 600)
      }
      onUpdate()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || '状態の更新に失敗しました')
    }
  }

  const handleDeleteReceipt = async () => {
    const confirmMessage = '本当にこの領収書を削除しますか？\n関連する仕訳データも削除されます。'
    if (!confirm(confirmMessage)) {
      return
    }
    
    try {
      const currentIndex = localReceipts.findIndex(r => r.id === receipt.id)
      
      await api.delete(`/videos/${videoId}/receipts/${receipt.id}`)
      toast.success('領収書を削除しました')
      
      // ローカル領収書リストから削除
      const updatedReceipts = localReceipts.filter(r => r.id !== receipt.id)
      setLocalReceipts(updatedReceipts)
      
      // 次の領収書に移動または前の領収書に移動
      if (updatedReceipts.length > 0) {
        let nextReceiptId
        if (currentIndex < updatedReceipts.length) {
          // 同じインデックスの領収書（次の領収書）に移動
          nextReceiptId = updatedReceipts[currentIndex].id
        } else if (currentIndex > 0) {
          // 前の領収書に移動
          nextReceiptId = updatedReceipts[currentIndex - 1].id
        } else {
          // 最初の領収書に移動
          nextReceiptId = updatedReceipts[0].id
        }
        
        if (onReceiptChange) {
          onReceiptChange(nextReceiptId)
        }
      } else {
        // すべての領収書が削除された場合のみモーダルを閉じる
        onClose()
      }
      
      onUpdate()
    } catch (error: any) {
      console.error('Delete receipt error:', error)
      toast.error(error.response?.data?.detail || '削除に失敗しました')
    }
  }

  if (!isOpen || !receipt) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg w-full h-full max-w-[100vw] max-h-[100vh] overflow-hidden flex">
          
          {/* 左側: 領収書リスト */}
          {showReceiptList && localReceipts.length > 0 && (
            <div className="w-36 bg-gray-50 border-r flex flex-col h-full">
              <div className="p-2 border-b bg-white flex-shrink-0">
                <h3 className="text-sm font-bold text-gray-900">領収書一覧</h3>
                <div className="flex items-center justify-between mt-0.5">
                  <p className="text-xs font-semibold text-gray-800">{localReceipts.length}件</p>
                  {/* 確認済み数 */}
                  {allJournals.filter((j: any) => j.status === 'confirmed').length > 0 && (
                    <div className="flex items-center gap-0.5">
                      <CheckIcon className="h-3 w-3 text-green-600" />
                      <span className="text-xs font-medium text-green-700">
                        {allJournals.filter((j: any) => j.status === 'confirmed').length}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex-1 overflow-y-auto min-h-0">
                {localReceipts.map((r, index) => {
                  // この領収書のjournalを検索
                  const relatedJournal = allJournals.find((j: any) => j.receipt_id === r.id)
                  const isJournalConfirmed = relatedJournal?.status === 'confirmed'
                  const isCurrentReceipt = r.id === receipt?.id
                  
                  return (
                    <button
                      key={r.id}
                      onClick={() => handleReceiptNavigation(r.id)}
                      className={`w-full p-2 text-left transition-all duration-200 border-b border-gray-200 relative overflow-hidden ${
                        isCurrentReceipt 
                          ? 'bg-gradient-to-r from-blue-100 to-blue-50 border-l-4 border-l-blue-600 shadow-md ring-1 ring-blue-200' 
                          : isJournalConfirmed
                          ? 'bg-gradient-to-r from-green-50 to-white hover:from-green-100 hover:to-green-50'
                          : 'hover:bg-gray-100'
                      }`}
                    >
                      {/* 現在選択中の領収書の背景効果 */}
                      {isCurrentReceipt && (
                        <div className="absolute inset-0 bg-blue-400 opacity-5 animate-pulse" />
                      )}
                      
                      <div className="flex items-start gap-1 relative">
                        <div className="flex flex-col items-center gap-0.5">
                          {/* 番号バッジ */}
                          <div className={`flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs ${
                            isCurrentReceipt 
                              ? 'bg-blue-600 text-white shadow-sm' 
                              : isJournalConfirmed
                              ? 'bg-green-600 text-white'
                              : 'bg-gray-200 text-gray-700'
                          }`}>
                            {index + 1}
                          </div>
                          
                          {/* 確認状態表示（大きめのチェックマーク） */}
                          {isJournalConfirmed && (
                            <div className="relative">
                              <div className="absolute -inset-1 bg-green-400 rounded-full opacity-30 animate-ping" />
                              <div className="relative bg-green-100 rounded-full p-0.5">
                                <CheckIcon className="h-4 w-4 text-green-700 font-bold" />
                              </div>
                            </div>
                          )}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          {/* 店舗名 */}
                          <p className={`text-xs font-bold truncate ${
                            isCurrentReceipt ? 'text-blue-900' : 'text-gray-900'
                          }`}>
                            {r.vendor || '不明'}
                          </p>
                          
                          {/* 金額（太字で強調） */}
                          <p className={`text-sm font-extrabold ${
                            isCurrentReceipt ? 'text-blue-800' : 'text-gray-800'
                          }`}>
                            ¥{r.total?.toLocaleString() || 0}
                          </p>
                          
                          {/* タイムスタンプ */}
                          <div className="flex items-center gap-1 mt-0.5">
                            <ClockIcon className="h-3 w-3 text-gray-400" />
                            <span className="text-xs text-gray-600">
                              {((r.best_frame?.time_ms || 0) / 1000).toFixed(1)}s
                            </span>
                          </div>
                          
                          {/* 手動追加バッジ */}
                          {r.is_manual && (
                            <span className="inline-block px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-medium mt-1">
                              手動
                            </span>
                          )}
                        </div>
                        
                        {/* 現在選択中インジケーター */}
                        {isCurrentReceipt && (
                          <div className="absolute -right-1 top-1/2 -translate-y-1/2">
                            <ChevronRightIcon className="h-5 w-5 text-blue-600 animate-bounce-horizontal" />
                          </div>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
              {/* 領収書ナビゲーションボタン */}
              <div className="p-1.5 border-t bg-white flex justify-between flex-shrink-0">
                <button
                  onClick={handlePrevReceipt}
                  disabled={currentReceiptIndex <= 0}
                  className="p-0.5 hover:bg-gray-100 rounded disabled:opacity-30"
                  title="前の領収書"
                >
                  <ChevronLeftIcon className="h-3 w-3 text-gray-600" />
                </button>
                <span className="text-xs font-bold text-gray-900 self-center">
                  {currentReceiptIndex + 1} / {allReceipts.length}
                </span>
                <button
                  onClick={handleNextReceipt}
                  disabled={currentReceiptIndex >= allReceipts.length - 1}
                  className="p-0.5 hover:bg-gray-100 rounded disabled:opacity-30"
                  title="次の領収書"
                >
                  <ChevronRightIcon className="h-3 w-3 text-gray-600" />
                </button>
              </div>
            </div>
          )}
          
          {/* メインコンテンツ領域 */}
          <div className="flex-1 flex flex-col h-full">
            {/* ヘッダー */}
            <div className="bg-gray-50 px-3 py-1.5 border-b flex justify-between items-center flex-shrink-0">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowReceiptList(!showReceiptList)}
                  className="p-1 hover:bg-gray-200 rounded transition-colors"
                  title={showReceiptList ? '一覧を隠す' : '一覧を表示'}
                >
                  {showReceiptList ? (
                    <ChevronLeftIcon className="h-4 w-4 text-gray-700" />
                  ) : (
                    <ChevronRightIcon className="h-4 w-4 text-gray-700" />
                  )}
                </button>
                <h2 className="text-base font-bold text-gray-900">
                  領収書と仕訳の編集
                  {receipt && (
                    <span className="ml-2 text-sm font-semibold text-gray-800">
                      - {receipt.vendor || '不明'}
                    </span>
                  )}
                </h2>
              </div>
              <div className="flex items-center gap-2">
                {/* 確認チェックボックス with インラインフィードバック */}
                <div className={`flex items-center gap-1.5 px-2 py-1 bg-white border rounded transition-all duration-300 ${
                  confirmAnimating ? 'scale-105 ring-2 ring-green-400' : ''
                } ${isConfirmed ? 'border-green-500 bg-green-50' : 'border-gray-300'}`}>
                  <input
                    type="checkbox"
                    id="confirm-check"
                    checked={isConfirmed}
                    onChange={handleToggleConfirm}
                    className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                  />
                  <label 
                    htmlFor="confirm-check" 
                    className={`text-xs font-medium cursor-pointer transition-colors ${isConfirmed ? 'text-green-700' : 'text-gray-700'}`}
                  >
                    {isConfirmed ? '確認済み' : '未確認'}
                  </label>
                  {/* アニメーション表示 - 確認時のみ */}
                  {confirmAnimating && isConfirmed && (
                    <div className="absolute -right-8 flex items-center">
                      <CheckIcon className="h-5 w-5 text-green-600 animate-bounce" />
                    </div>
                  )}
                </div>
                {/* 削除ボタン */}
                <button
                  onClick={handleDeleteReceipt}
                  className="px-2 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs flex items-center gap-1 transition-colors"
                  title="この領収書を削除"
                >
                  <TrashIcon className="h-3.5 w-3.5" />
                  削除
                </button>
                <button
                  onClick={onClose}
                  className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  <XMarkIcon className="h-4 w-4 text-gray-600" />
                </button>
              </div>
            </div>

            {/* コンテンツ */}
            <div className="flex flex-1 min-h-0">
          {/* 左側: 領収書画像 */}
          <div className="flex-1 border-r bg-gray-50 flex flex-col min-w-0">
            <div className="space-y-1 p-1">
              {/* フレーム制御ボタン */}
              {
              <div className="bg-white rounded p-1 border">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-medium text-gray-700">フレーム</span>
                  <span className="text-xs text-gray-700 font-medium">
                    {(currentFrameTime / 1000).toFixed(1)}s
                  </span>
                </div>
                <div className="flex gap-1">
                  {/* 戻るボタン */}
                  <div className="flex gap-0.5 bg-white rounded border p-0.5">
                    <button
                      onClick={() => handleFrameNavigation('prev', 'second')}
                      disabled={isLoadingFrame}
                      className="px-1 py-0.5 hover:bg-blue-50 rounded text-xs text-gray-700 font-medium disabled:opacity-50"
                      title="1秒戻る"
                    >
                      -1s
                    </button>
                    <button
                      onClick={() => handleFrameNavigation('prev', 'halfSecond')}
                      disabled={isLoadingFrame}
                      className="px-1 py-0.5 hover:bg-blue-50 rounded text-xs text-gray-700 font-medium disabled:opacity-50"
                      title="0.5秒戻る"
                    >
                      -.5s
                    </button>
                    <button
                      onClick={() => handleFrameNavigation('prev', 'frame')}
                      disabled={isLoadingFrame}
                      className="px-1 py-0.5 hover:bg-blue-50 rounded text-xs text-gray-700 font-medium disabled:opacity-50"
                      title="1フレーム戻る"
                    >
                      <ChevronLeftIcon className="h-3 w-3 text-gray-600" />
                    </button>
                  </div>
                  
                  {/* 進むボタン */}
                  <div className="flex gap-0.5 bg-white rounded border p-0.5">
                    <button
                      onClick={() => handleFrameNavigation('next', 'frame')}
                      disabled={isLoadingFrame}
                      className="px-1 py-0.5 hover:bg-blue-50 rounded text-xs text-gray-700 font-medium disabled:opacity-50"
                      title="1フレーム進む"
                    >
                      <ChevronRightIcon className="h-3 w-3 text-gray-600" />
                    </button>
                    <button
                      onClick={() => handleFrameNavigation('next', 'halfSecond')}
                      disabled={isLoadingFrame}
                      className="px-1 py-0.5 hover:bg-blue-50 rounded text-xs text-gray-700 font-medium disabled:opacity-50"
                      title="0.5秒進む"
                    >
                      +.5s
                    </button>
                    <button
                      onClick={() => handleFrameNavigation('next', 'second')}
                      disabled={isLoadingFrame}
                      className="px-1 py-0.5 hover:bg-blue-50 rounded text-xs text-gray-700 font-medium disabled:opacity-50"
                      title="1秒進む"
                    >
                      +1s
                    </button>
                  </div>
                </div>
              </div>
              }
              
              {/* OCR分析オプション - コンパクトUI */}
              <div className="bg-blue-50 rounded p-1 border border-blue-200">
                <div className="text-xs font-medium text-blue-900 mb-0.5">OCRモード</div>
                <div className="flex gap-0.5">
                  <label className={`flex items-center justify-center px-1.5 py-1 rounded cursor-pointer transition-all ${
                    ocrApplyMode === 'overwrite' 
                      ? 'bg-blue-600 text-white shadow-md' 
                      : 'bg-white text-gray-700 border hover:bg-blue-50'
                  }`}>
                    <input
                      type="radio"
                      name="ocrMode"
                      value="overwrite"
                      checked={ocrApplyMode === 'overwrite'}
                      onChange={(e) => setOcrApplyMode(e.target.value as 'overwrite')}
                      className="sr-only"
                    />
                    <PencilIcon className="h-3 w-3 mr-0.5" />
                    <span className="text-xs">上書き</span>
                  </label>
                  
                  <label className={`flex items-center justify-center px-1.5 py-1 rounded cursor-pointer transition-all ${
                    ocrApplyMode === 'new' 
                      ? 'bg-green-600 text-white shadow-md' 
                      : 'bg-white text-gray-700 border hover:bg-green-50'
                  }`}>
                    <input
                      type="radio"
                      name="ocrMode"
                      value="new"
                      checked={ocrApplyMode === 'new'}
                      onChange={(e) => setOcrApplyMode(e.target.value as 'new')}
                      className="sr-only"
                    />
                    <PlusIcon className="h-3 w-3 mr-0.5" />
                    <span className="text-xs">新規</span>
                  </label>
                  
                  <button
                    onClick={handleReanalyzeFrame}
                    disabled={isAnalyzing || isLoadingFrame}
                    className={`flex items-center justify-center px-2 py-1 rounded text-xs transition-all ml-auto ${
                      isAnalyzing || isLoadingFrame
                        ? 'bg-gray-200 text-gray-600 cursor-not-allowed'
                        : ocrApplyMode === 'overwrite'
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-green-600 text-white hover:bg-green-700'
                    }`}
                  >
                    {isAnalyzing ? (
                      <>
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-1"></div>
                        分析中...
                      </>
                    ) : (
                      <>
                        <CameraIcon className="h-3 w-3 mr-1" />
                        分析実行
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
            
            
            {/* ビデオ要素（非表示） */}
            <video
              ref={hiddenVideoRef}
              style={{ display: 'none' }}
              crossOrigin="anonymous"
              preload="auto"
              muted
            />
            
            {/* ビデオロード状態表示 */}
            {!videoLoaded && (
              <div className="absolute top-0 left-0 right-0 bg-yellow-100 text-yellow-800 text-xs p-1 text-center">
                🎬 ビデオをロード中...
              </div>
            )}
            
            {/* Canvasでフレーム表示 */}
            {(
              <div 
                ref={imageContainerRef}
                className="flex-1 min-h-0 relative bg-gray-900 overflow-hidden"
                onWheel={(e) => {
                  e.preventDefault()
                  const delta = e.deltaY > 0 ? 0.9 : 1.1
                  const newZoom = Math.min(Math.max(zoomLevel * delta, 1), 5)
                  setZoomLevel(newZoom)
                  if (newZoom === 1) {
                    setImagePosition({ x: 0, y: 0 })
                  }
                }}
              >
                <canvas
                  ref={canvasRef}
                  className={`absolute ${imageViewMode === 'contain' ? 'object-contain' : 'object-cover'} ${zoomLevel > 1 ? 'cursor-move' : 'cursor-default'}`}
                  style={{
                    width: `${100 * zoomLevel}%`,
                    height: `${100 * zoomLevel}%`,
                    left: '50%',
                    top: '50%',
                    transform: `translate(calc(-50% + ${imagePosition.x}px), calc(-50% + ${imagePosition.y}px))`,
                    transition: isDragging ? 'none' : 'transform 0.2s'
                  }}
                  onMouseDown={(e) => {
                    if (zoomLevel > 1) {
                      setIsDragging(true)
                      setDragStart({ x: e.clientX - imagePosition.x, y: e.clientY - imagePosition.y })
                      e.preventDefault()
                    }
                  }}
                  onMouseMove={(e) => {
                    if (isDragging && zoomLevel > 1) {
                      const newX = e.clientX - dragStart.x
                      const newY = e.clientY - dragStart.y
                      const maxOffset = ((zoomLevel - 1) * 100) / 2
                      setImagePosition({
                        x: Math.min(Math.max(newX, -maxOffset * 3), maxOffset * 3),
                        y: Math.min(Math.max(newY, -maxOffset * 3), maxOffset * 3)
                      })
                    }
                  }}
                  onMouseUp={() => setIsDragging(false)}
                  onMouseLeave={() => setIsDragging(false)}
                />
                {isLoadingFrame && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
                  </div>
                )}
                {/* コントロールボタン */}
                <div className="absolute top-2 right-2 flex gap-1">
                  {/* ズームコントロール */}
                  <div className="bg-black/50 rounded flex items-center px-1">
                    <button
                      onClick={() => {
                        const newZoom = Math.max(zoomLevel - 0.5, 1)
                        setZoomLevel(newZoom)
                        if (newZoom === 1) setImagePosition({ x: 0, y: 0 })
                      }}
                      className="text-white p-1 hover:bg-white/20 rounded transition-colors"
                      disabled={zoomLevel <= 1}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                      </svg>
                    </button>
                    <span className="text-white text-xs mx-1 min-w-[3em] text-center">
                      {Math.round(zoomLevel * 100)}%
                    </span>
                    <button
                      onClick={() => {
                        const newZoom = Math.min(zoomLevel + 0.5, 5)
                        setZoomLevel(newZoom)
                      }}
                      className="text-white p-1 hover:bg-white/20 rounded transition-colors"
                      disabled={zoomLevel >= 5}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                    </button>
                    {zoomLevel > 1 && (
                      <button
                        onClick={() => {
                          setZoomLevel(1)
                          setImagePosition({ x: 0, y: 0 })
                        }}
                        className="text-white p-1 hover:bg-white/20 rounded transition-colors ml-1"
                        title="リセット"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      </button>
                    )}
                  </div>
                  
                  {/* 表示モードトグル */}
                  <button
                    onClick={() => setImageViewMode(imageViewMode === 'contain' ? 'cover' : 'contain')}
                    className="bg-black/50 hover:bg-black/70 text-white p-1.5 rounded transition-colors"
                    title={imageViewMode === 'contain' ? '画面に合わせる' : '全体表示'}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      {imageViewMode === 'contain' ? (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                      ) : (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                      )}
                    </svg>
                  </button>
                </div>
                
                {/* ズーム/パン案内 */}
                {zoomLevel > 1 && (
                  <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                    ドラッグで移動
                  </div>
                )}
              </div>
            )}
            <div className="px-1 pb-1">
              {/* タイムライン表示 */}
              {videoDuration > 0 && (
                <div className="bg-gradient-to-b from-gray-50 to-gray-100 rounded-lg p-2 border border-gray-200">
                  <div className="flex items-center justify-between text-xs text-gray-700 mb-1">
                    <span className="font-medium">0.0s</span>
                    <span className="font-bold text-sm text-blue-600">
                      {(Math.max(0, currentFrameTime) / 1000).toFixed(1)}s
                    </span>
                    <span className="font-medium">{videoDuration.toFixed(1)}s</span>
                  </div>
                  
                  {/* タイムラインバー */}
                  <div 
                    className="relative h-6 bg-gradient-to-r from-gray-200 to-gray-300 rounded-lg overflow-hidden shadow-inner cursor-pointer group"
                    onClick={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect()
                      const x = e.clientX - rect.left
                      const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
                      const newTime = Math.floor((percentage / 100) * videoDuration * 1000)
                      setCurrentFrameTime(newTime)
                      // ビデオシーク
                      if (hiddenVideoRef.current && videoLoaded) {
                        hiddenVideoRef.current.currentTime = newTime / 1000
                        // seekedイベントでキャプチャされる
                      }
                    }}
                  >
                    {/* 背景グラデーション効果 */}
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/10 to-transparent pointer-events-none" />
                    
                    {/* プログレスバー（現在位置まで） */}
                    <div 
                      className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-200 shadow-sm"
                      style={{ 
                        width: `${Math.max(0, Math.min(100, ((Math.max(0, currentFrameTime) / 1000 / videoDuration) * 100)))}%` 
                      }}
                    >
                      {/* プログレスバーの光沢効果 */}
                      <div className="absolute inset-0 bg-gradient-to-b from-white/20 to-transparent" />
                    </div>
                    
                    {/* 他の領収書マーカー */}
                    {localReceipts.map((r: any) => {
                      if (r.id === receipt?.id) return null
                      const position = Math.max(0, Math.min(100, ((r.best_frame?.time_ms || 0) / 1000 / videoDuration) * 100))
                      return (
                        <div
                          key={r.id}
                          className="absolute top-1 bottom-1 w-1 bg-gray-600/60 rounded-full hover:bg-gray-700 hover:scale-x-150 transition-all cursor-pointer"
                          style={{ left: `${position}%`, transform: 'translateX(-50%)' }}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleReceiptNavigation(r.id)
                          }}
                          title={`${r.vendor || '不明'} - ${((r.best_frame?.time_ms || 0) / 1000).toFixed(1)}秒`}
                        >
                          {/* ホバー時のハイライト */}
                          <div className="absolute inset-0 bg-yellow-400/50 rounded-full scale-0 group-hover:scale-150 transition-transform" />
                        </div>
                      )
                    })}
                    
                    {/* 現在の領収書の元の位置インジケーター */}
                    {receipt?.best_frame?.time_ms !== undefined && receipt.best_frame.time_ms !== currentFrameTime && (
                      <div 
                        className="absolute top-1/2 -translate-y-1/2 w-2 h-2 bg-blue-300 rounded-full border border-blue-500 opacity-50"
                        style={{ 
                          left: `${Math.max(0, Math.min(100, ((receipt.best_frame.time_ms / 1000 / videoDuration) * 100)))}%`
                        }}
                        title="元の位置"
                      />
                    )}
                    
                    {/* 現在位置マーカー（ドラッグ可能風の見た目） */}
                    <div 
                      className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full border-2 border-blue-600 shadow-lg hover:scale-110 transition-transform cursor-grab active:cursor-grabbing z-10"
                      style={{ 
                        left: `${Math.max(0, Math.min(100, ((Math.max(0, currentFrameTime) / 1000 / videoDuration) * 100)))}%`,
                        transform: 'translate(-50%, -50%)'
                      }}
                    >
                      {/* 内側の点 */}
                      <div className="absolute inset-1 bg-blue-600 rounded-full" />
                    </div>
                    
                    {/* ホバー時の時間表示 */}
                    <div className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-0.5 rounded whitespace-nowrap">
                        クリックで移動
                      </div>
                    </div>
                  </div>
                  
                  {/* 補助情報 */}
                  <div className="flex items-center justify-between mt-1">
                    <div className="flex items-center gap-2 text-xs">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-gray-600/60 rounded-full" />
                        <span className="text-gray-700">他の領収書</span>
                      </div>
                      {receipt?.best_frame?.time_ms !== undefined && receipt.best_frame.time_ms !== currentFrameTime && (
                        <div className="flex items-center gap-1">
                          <div className="w-2 h-2 bg-blue-300 rounded-full border border-blue-500" />
                          <span className="text-gray-700">元の位置</span>
                        </div>
                      )}
                    </div>
                    {receipt.is_manual && (
                      <span className="text-xs text-green-600 font-medium">手動追加</span>
                    )}
                  </div>
                </div>
              )}
              
              {/* 既存の時間情報 */}
              {receipt.is_manual && (
                <div className="text-xs text-blue-600 text-center mt-1">手動追加</div>
              )}
            </div>
          </div>

          {/* データ編集エリア (領収書 + 仕訳) */}
          <div className="flex flex-col border-l border-gray-200">
            {/* 統合保存ボタン - データ列の上部 */}
            <div className="flex bg-blue-50 border-b-2 border-blue-300">
              <button
                onClick={handleSaveAll}
                disabled={isSaving}
                className="w-full px-3 py-2 bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {isSaving ? (
                  <>
                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                    保存中...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V2" />
                    </svg>
                    領収書 & 仕訳データを保存
                  </>
                )}
              </button>
            </div>
            
            <div className="flex flex-1">
              {/* 領収書データ列 */}
              <div className="w-44 p-2 flex flex-col">
                <h3 className="font-bold text-sm text-gray-900 mb-2">領収書データ</h3>

            <div className="space-y-1">
              <div>
                <label className="text-xs text-gray-700 font-medium block">店舗</label>
                <input
                  type="text"
                  value={receiptForm.vendor}
                  onChange={(e) => setReceiptForm({...receiptForm, vendor: e.target.value})}
                  
                  className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-1">
                <div>
                  <label className="text-xs text-gray-700 font-medium block">金額</label>
                  <input
                    type="number"
                    value={receiptForm.total}
                    onChange={(e) => setReceiptForm({...receiptForm, total: e.target.value})}
                    
                    className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-700 font-medium block">税額</label>
                  <input
                    type="number"
                    value={receiptForm.tax}
                    onChange={(e) => setReceiptForm({...receiptForm, tax: e.target.value})}
                    
                    className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-gray-700 font-medium block">発行日</label>
                <input
                  type="date"
                  value={receiptForm.issue_date}
                  onChange={(e) => setReceiptForm({...receiptForm, issue_date: e.target.value})}
                  
                  className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs text-gray-700 font-medium block">支払</label>
                <select
                  value={receiptForm.payment_method}
                  onChange={(e) => setReceiptForm({...receiptForm, payment_method: e.target.value})}
                  
                  className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none"
                >
                  <option value="">選択してください</option>
                  <option value="現金">現金</option>
                  <option value="クレジット">クレジット</option>
                  <option value="電子マネー">電子マネー</option>
                  <option value="不明">不明</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-gray-700 font-medium block">メモ</label>
                <textarea
                  value={receiptForm.memo}
                  onChange={(e) => setReceiptForm({...receiptForm, memo: e.target.value})}
                  
                  className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none"
                  rows={1}
                />
                </div>
              </div>
              </div>

              {/* 仕訳データ列 */}
              <div className="w-44 p-2 bg-gray-50 flex flex-col">
                <h3 className="font-bold text-sm text-gray-900 mb-2">仕訳データ</h3>

            {journal ? (
              <div className="space-y-1.5">
                <div className="grid grid-cols-2 gap-1">
                  <div>
                    <label className="text-xs text-gray-700 font-medium">借方科目</label>
                    <input
                      type="text"
                      value={journalForm.debit_account}
                      onChange={(e) => setJournalForm({...journalForm, debit_account: e.target.value})}
                      
                      className="w-full p-1 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none bg-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-700 font-medium">借方金額</label>
                    <input
                      type="number"
                      value={journalForm.debit_amount}
                      onChange={(e) => setJournalForm({...journalForm, debit_amount: e.target.value})}
                      
                      className="w-full p-1 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none bg-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-1">
                  <div>
                    <label className="text-xs text-gray-700 font-medium">貸方科目</label>
                    <input
                      type="text"
                      value={journalForm.credit_account}
                      onChange={(e) => setJournalForm({...journalForm, credit_account: e.target.value})}
                      
                      className="w-full p-1 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none bg-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-700 font-medium">貸方金額</label>
                    <input
                      type="number"
                      value={journalForm.credit_amount}
                      onChange={(e) => setJournalForm({...journalForm, credit_amount: e.target.value})}
                      
                      className="w-full p-1 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none bg-white"
                    />
                  </div>
                </div>

                {journalForm.tax_account && (
                  <div className="grid grid-cols-2 gap-1">
                    <div>
                      <label className="text-xs text-gray-700 font-medium block">税科目</label>
                      <input
                        type="text"
                        value={journalForm.tax_account}
                        onChange={(e) => setJournalForm({...journalForm, tax_account: e.target.value})}
                        
                        className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none bg-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-700 font-medium block">税額</label>
                      <input
                        type="number"
                        value={journalForm.tax_amount}
                        onChange={(e) => setJournalForm({...journalForm, tax_amount: e.target.value})}
                        
                        className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none bg-white"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="text-xs text-gray-700 font-medium block">摘要</label>
                  <textarea
                    value={journalForm.memo}
                    onChange={(e) => setJournalForm({...journalForm, memo: e.target.value})}
                    className="w-full px-1 py-0.5 text-xs text-gray-900 font-medium border rounded hover:border-blue-400 focus:border-blue-500 focus:outline-none bg-white"
                    rows={1}
                  />
                </div>

                </div>
              ) : (
                <div className="text-center py-4 text-gray-700 text-xs">
                  仕訳データがありません
                </div>
              )}
              </div>
            </div>
          </div>
        </div>
        </div>
      </div>
    </div>

    {/* OCR結果確認ダイアログ - もう使用しない */}
    {false && showOcrConfirmDialog && ocrPreviewData && (
      <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
        <div className="bg-white rounded-lg max-w-lg w-full p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">OCR分析結果</h3>
          
          <div className="space-y-3 mb-6 max-h-60 overflow-y-auto">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-700 font-medium">店舗名:</span>
                <span className="ml-2 font-medium text-gray-800">{ocrPreviewData.vendor || '不明'}</span>
              </div>
              <div>
                <span className="text-gray-700 font-medium">金額:</span>
                <span className="ml-2 font-medium text-gray-800">¥{ocrPreviewData.total?.toLocaleString() || 0}</span>
              </div>
              <div>
                <span className="text-gray-700 font-medium">税額:</span>
                <span className="ml-2 font-medium text-gray-800">¥{ocrPreviewData.tax?.toLocaleString() || 0}</span>
              </div>
              <div>
                <span className="text-gray-700 font-medium">日付:</span>
                <span className="ml-2 font-medium text-gray-800">
                  {ocrPreviewData.issue_date ? 
                    (typeof ocrPreviewData.issue_date === 'string' 
                      ? ocrPreviewData.issue_date.split('T')[0]
                      : format(new Date(ocrPreviewData.issue_date), 'yyyy-MM-dd'))
                    : '不明'}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-700 font-medium">支払方法:</span>
                <span className="ml-2 font-medium text-gray-800">{ocrPreviewData.payment_method || '不明'}</span>
              </div>
            </div>
          </div>
          
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6">
            <p className="text-sm text-blue-800 font-medium mb-2">
              データの適用方法を選択してください:
            </p>
            <div className="space-y-2">
              <label className="flex items-center cursor-pointer hover:bg-blue-100 p-2 rounded transition-colors">
                <input
                  type="radio"
                  name="applyMode"
                  value="overwrite"
                  defaultChecked
                  className="mr-2"
                />
                <div>
                  <span className="text-sm font-medium text-gray-900">現在の領収書を上書き</span>
                  <p className="text-xs text-gray-700">現在編集中の領収書データを置き換えます</p>
                </div>
              </label>
              <label className="flex items-center cursor-pointer hover:bg-blue-100 p-2 rounded transition-colors">
                <input
                  type="radio"
                  name="applyMode"
                  value="new"
                  className="mr-2"
                />
                <div>
                  <span className="text-sm font-medium text-gray-900">新しい領収書として追加</span>
                  <p className="text-xs text-gray-700">現在の領収書はそのまま残し、新規作成します</p>
                </div>
              </label>
            </div>
          </div>
          
          <div className="flex justify-end gap-3">
            <button
              onClick={handleCancelOcrData}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              キャンセル
            </button>
            <button
              onClick={() => {
                const selectedMode = (document.querySelector('input[name="applyMode"]:checked') as HTMLInputElement)?.value
                if (selectedMode === 'new') {
                  handleCreateNewReceipt()
                } else {
                  handleApplyOcrData()
                }
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              適用
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  )
}