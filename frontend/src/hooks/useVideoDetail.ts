import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useVideoDetail(videoId: number) {
  return useQuery({
    queryKey: ['video', videoId],
    queryFn: async () => {
      const response = await api.get(`/videos/${videoId}`)
      return response.data
    },
    enabled: !!videoId,
    staleTime: 0, // データを即座に古いとみなす
    gcTime: 5 * 60 * 1000, // 5分間キャッシュ保持
    refetchOnWindowFocus: true, // ウィンドウフォーカス時に再取得
    refetchOnMount: true, // マウント時に再取得
  })
}