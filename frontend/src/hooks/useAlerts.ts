import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { acknowledgeAlert, getAlerts, resolveAlert } from '../api/alerts'
import type { AlertRead } from '../types'

export function useAlerts(status?: string) {
  return useQuery<AlertRead[]>({
    queryKey: ['alerts', status ?? 'all'],
    queryFn: () => getAlerts(status),
    refetchInterval: 30_000,
  })
}

export function useResolveAlert() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: resolveAlert,
    onSuccess: () => client.invalidateQueries({ queryKey: ['alerts'] }),
  })
}

export function useAcknowledgeAlert() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => client.invalidateQueries({ queryKey: ['alerts'] }),
  })
}
