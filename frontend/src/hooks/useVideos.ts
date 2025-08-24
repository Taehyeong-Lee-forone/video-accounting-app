import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useEffect } from 'react'

export function useVideos() {
  const query = useQuery({
    queryKey: ['videos'],
    queryFn: async () => {
      const response = await api.get('/videos/')
      return response.data
    },
    // 1秒ごとに必ずリフレッシュ
    refetchInterval: 1000,
    refetchIntervalInBackground: true,
    staleTime: 0,
    gcTime: 0, // キャッシュを即座に削除
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  })

  // 処理中のビデオがなければ自動リフレッシュを停止
  useEffect(() => {
    if (Array.isArray(query.data)) {
      const hasProcessing = query.data.some((video: any) => 
        ['processing', 'queued', 'PROCESSING', 'QUEUED'].includes(video.status)
      )
      if (!hasProcessing) {
        // 処理中のビデオがなければrefetch間隔を大きくする
        setTimeout(() => {
          query.refetch()
        }, 5000)
      }
    }
  }, [query.data])

  return query
}