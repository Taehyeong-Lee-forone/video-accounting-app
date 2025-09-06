'use client'

import { useJournalHistory } from '@/contexts/JournalHistoryContext'
import { useRouter } from 'next/navigation'
import { ClockIcon, DocumentTextIcon, FilmIcon, TrashIcon } from '@heroicons/react/24/outline'
import { formatDistanceToNow } from 'date-fns'
import { ja } from 'date-fns/locale'

export default function JournalHistory() {
  const { history, removeFromHistory, clearHistory } = useJournalHistory()
  const router = useRouter()

  const handleResumeSession = (videoId: number) => {
    router.push(`/review/${videoId}`)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (history.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-8 text-center">
        <ClockIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">履歴がありません</h3>
        <p className="text-gray-500">
          仕訳作成を開始すると、ここに履歴が表示されます
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm">
      <div className="p-4 border-b flex justify-between items-center">
        <h2 className="text-lg font-semibold text-gray-900">最近の作業履歴</h2>
        <button
          onClick={() => {
            if (confirm('すべての履歴を削除してもよろしいですか？')) {
              clearHistory()
            }
          }}
          className="text-sm text-red-600 hover:text-red-700"
        >
          すべてクリア
        </button>
      </div>

      <div className="divide-y divide-gray-200">
        {history.map((item) => (
          <div
            key={item.id}
            className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
            onClick={() => handleResumeSession(item.videoId)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <FilmIcon className="h-5 w-5 text-gray-400" />
                  <h3 className="font-medium text-gray-900">
                    {item.videoTitle || `動画 #${item.videoId}`}
                  </h3>
                </div>

                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <div className="flex items-center gap-1">
                    <ClockIcon className="h-4 w-4" />
                    <span>再生位置: {formatTime(item.currentTime)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <DocumentTextIcon className="h-4 w-4" />
                    <span>領収書: {item.totalReceipts}件</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <DocumentTextIcon className="h-4 w-4" />
                    <span>仕訳: {item.totalJournals}件</span>
                  </div>
                </div>

                <div className="mt-2 text-xs text-gray-500">
                  最終アクセス: {formatDistanceToNow(item.lastAccessedAt, { 
                    addSuffix: true,
                    locale: ja 
                  })}
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation()
                  removeFromHistory(item.id)
                }}
                className="ml-4 p-2 text-gray-400 hover:text-red-600 transition-colors"
              >
                <TrashIcon className="h-5 w-5" />
              </button>
            </div>

            {item.thumbnailUrl && (
              <div className="mt-3">
                <img
                  src={item.thumbnailUrl}
                  alt="サムネイル"
                  className="h-20 w-32 object-cover rounded"
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}