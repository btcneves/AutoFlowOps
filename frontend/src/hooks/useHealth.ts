import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/health'

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    retry: 2,
    refetchInterval: 30_000,
  })
}
