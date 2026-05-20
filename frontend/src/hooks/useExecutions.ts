import { useQuery } from '@tanstack/react-query'
import { getExecution, getExecutions } from '../api/executions'
import type { ExecutionFilters } from '../api/executions'

export function useExecutions(filters?: ExecutionFilters) {
  return useQuery({
    queryKey: ['executions', filters],
    queryFn: () => getExecutions(filters),
    refetchInterval: 15_000,
  })
}

export function useExecution(id: string) {
  return useQuery({
    queryKey: ['executions', id],
    queryFn: () => getExecution(id),
  })
}
