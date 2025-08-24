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
  })
}