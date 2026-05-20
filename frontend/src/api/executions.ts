import { apiFetch } from './client'
import type { ExecutionRead } from '../types'

export interface ExecutionFilters {
  job_id?: string
  status?: string
  limit?: number
  offset?: number
}

export function getExecutions(filters?: ExecutionFilters): Promise<ExecutionRead[]> {
  const params = new URLSearchParams()
  if (filters?.job_id) params.set('job_id', filters.job_id)
  if (filters?.status) params.set('status', filters.status)
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit))
  if (filters?.offset !== undefined) params.set('offset', String(filters.offset))
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch<ExecutionRead[]>(`/api/executions${qs}`)
}

export function getExecution(id: string): Promise<ExecutionRead> {
  return apiFetch<ExecutionRead>(`/api/executions/${id}`)
}
