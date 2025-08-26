import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useJournals(videoId?: number) {
  return useQuery({
    queryKey: ['journals', videoId],
    queryFn: async () => {
      const params = videoId ? `?video_id=${videoId}` : ''
      const response = await api.get(`/journals${params}`)
      return response.data
    },
    staleTime: 0, // データを即座に古いとみなす
    gcTime: 5 * 60 * 1000, // 5分間キャッシュ保持
    refetchOnWindowFocus: true, // ウィンドウフォーカス時に再取得
    refetchOnMount: true, // マウント時に再取得
  })
}