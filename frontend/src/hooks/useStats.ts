import { useQuery } from '@tanstack/react-query'
import { getMyStats } from '../api/stats'

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: getMyStats,
    staleTime: 5 * 60 * 1000,
  })
}
