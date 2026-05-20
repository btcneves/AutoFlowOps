import { useQuery } from '@tanstack/react-query'
import { getStats } from '../api/stats'
import type { StatsResponse } from '../types'

export function useStats() {
  return useQuery<StatsResponse>({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: 30_000,
  })
}
