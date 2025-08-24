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
  })
}