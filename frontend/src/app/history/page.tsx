'use client'

import JournalHistory from '@/components/JournalHistory'
import { useJournalHistory } from '@/contexts/JournalHistoryContext'
import { ClockIcon } from '@heroicons/react/24/outline'

export default function HistoryPage() {
  const { history } = useJournalHistory()

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <ClockIcon className="h-8 w-8" />
          作業履歴
        </h1>
        <p className="mt-2 text-gray-600">
          最近作業した仕訳作成セッションの履歴です。クリックして作業を再開できます。
        </p>
        {history.length > 0 && (
          <p className="mt-1 text-sm text-gray-500">
            {history.length}件の履歴があります（最大10件まで保存）
          </p>
        )}
      </div>

      <JournalHistory />
    </div>
  )
}