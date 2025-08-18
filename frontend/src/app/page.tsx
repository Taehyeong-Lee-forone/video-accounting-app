'use client'

import { useState } from 'react'
import VideoUpload from '@/components/VideoUpload'
import VideoList from '@/components/VideoList'
import { useVideos } from '@/hooks/useVideos'

export default function Home() {
  const [selectedTab, setSelectedTab] = useState<'upload' | 'list'>('upload')
  const { refetch } = useVideos()

  return (
    <div className="max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">動画会計アプリ</h1>
      
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setSelectedTab('upload')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                selectedTab === 'upload'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              動画アップロード
            </button>
            <button
              onClick={() => setSelectedTab('list')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                selectedTab === 'list'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              動画一覧
            </button>
          </nav>
        </div>
      </div>

      <div className="mt-6">
        {selectedTab === 'upload' ? (
          <VideoUpload onUploadSuccess={() => {
            refetch()
            setSelectedTab('list')
          }} />
        ) : (
          <VideoList />
        )}
      </div>
    </div>
  )
}