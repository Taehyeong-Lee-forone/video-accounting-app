'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { CloudArrowUpIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'
import { useVideoProgress } from '@/hooks/useVideoProgress'

interface VideoUploadProps {
  onUploadSuccess: () => void
}

export default function VideoUpload({ onUploadSuccess }: VideoUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [analysisVideoId, setAnalysisVideoId] = useState<number | null>(null)
  
  const { progress, startPolling, stopPolling } = useVideoProgress(
    analysisVideoId,
    analysisVideoId !== null
  )

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploading(true)
    setUploadProgress(0)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/videos/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0
          setUploadProgress(progress)
        },
      })

      toast.success('動画をアップロードしました')
      onUploadSuccess()
      
      // アップロード時に自動的に分析が開始されるため、進行状況追跡のみ開始
      const videoId = response.data.id
      setAnalysisVideoId(videoId)
      
      // analyze APIを呼ばずに、進行状況の追跡のみ開始
      startPolling()
      toast.success('分析を開始しました - 進行状況を表示します')
    } catch (error: any) {
      console.error('Upload error:', error)
      // エラーの詳細をログに出力
      if (error.response) {
        console.error('Error response:', error.response.data)
        toast.error(`アップロードに失敗しました: ${error.response.data?.detail || error.message}`)
      } else {
        toast.error('アップロードに失敗しました')
      }
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }, [onUploadSuccess, startPolling])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.webm', '.mkv'],
      'video/quicktime': ['.mov', '.qt'],  // QuickTime専用
      'video/mp4': ['.mp4', '.m4v'],
      'video/x-msvideo': ['.avi'],
      'video/webm': ['.webm'],
      'video/x-matroska': ['.mkv']
    },
    maxFiles: 1,
    disabled: uploading,
  })

  return (
    <div className="card">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-gray-400'
        } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">
          {isDragActive
            ? 'ここにドロップしてください'
            : 'クリックまたはドラッグ&ドロップで動画をアップロード'}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          MP4, MOV, AVI形式 (最大500MB)
        </p>
      </div>

      {/* アップロード進行率 */}
      {uploading && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>アップロード中...</span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}
      
      {/* 分析進行率 */}
      {progress && progress.status !== 'queued' && (
        <div className="mt-4 p-4 bg-primary-50 border border-primary-200 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-primary-800">
              {progress.status === 'done' || progress.status === 'DONE' ? (
                <>
                  <CheckCircleIcon className="h-4 w-4 inline mr-1 text-green-600" />
                  分析完了
                </>
              ) : progress.status === 'error' || progress.status === 'ERROR' ? (
                '分析エラー'
              ) : (
                '分析中...'
              )}
            </h3>
            <span className="text-sm font-medium text-primary-800">
              {progress.progress}%
            </span>
          </div>
          
          {progress.progress_message && (
            <p className="text-xs text-primary-600 mb-2">
              {progress.progress_message}
            </p>
          )}
          
          <div className="w-full bg-primary-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${
                progress.status === 'done' || progress.status === 'DONE'
                  ? 'bg-green-500'
                  : progress.status === 'error' || progress.status === 'ERROR'
                  ? 'bg-red-500'
                  : 'bg-primary'
              }`}
              style={{ width: `${progress.progress}%` }}
            />
          </div>
          
          {progress.error_message && (
            <p className="text-xs text-red-600 mt-2">
              エラー: {progress.error_message}
            </p>
          )}
          
          {(progress.status === 'done' || progress.status === 'DONE') && (
            <button
              onClick={() => {
                setAnalysisVideoId(null)
                stopPolling()
              }}
              className="mt-2 text-xs text-blue-600 hover:text-blue-800"
            >
              閉じる
            </button>
          )}
        </div>
      )}
    </div>
  )
}