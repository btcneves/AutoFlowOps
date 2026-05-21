import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAlertRule,
  deleteAlertRule,
  getAlertRules,
  updateAlertRule,
} from '../api/alert_rules'
import type { AlertRuleCreate, AlertRuleUpdate } from '../types'

export function useAlertRules(jobId: string) {
  return useQuery({
    queryKey: ['alert-rules', jobId],
    queryFn: () => getAlertRules(jobId),
  })
}

export function useCreateAlertRule(jobId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (payload: AlertRuleCreate) => createAlertRule(jobId, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['alert-rules', jobId] })
      client.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useUpdateAlertRule(jobId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AlertRuleUpdate }) =>
      updateAlertRule(jobId, id, payload),
    onSuccess: () => client.invalidateQueries({ queryKey: ['alert-rules', jobId] }),
  })
}

export function useDeleteAlertRule(jobId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteAlertRule(jobId, id),
    onSuccess: () => client.invalidateQueries({ queryKey: ['alert-rules', jobId] }),
  })
}
