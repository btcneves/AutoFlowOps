import { apiFetch } from './client'
import type { AuditLogRead } from '../types'

export interface AuditLogFilters {
  action?: string
  resource_type?: string
  status?: string
  since?: string
  until?: string
  limit?: number
}

export function getAuditLogs(filters: AuditLogFilters = {}): Promise<AuditLogRead[]> {
  const params = new URLSearchParams()
  if (filters.action) params.set('action', filters.action)
  if (filters.resource_type) params.set('resource_type', filters.resource_type)
  if (filters.status) params.set('status', filters.status)
  if (filters.since) params.set('since', filters.since)
  if (filters.until) params.set('until', filters.until)
  if (filters.limit != null) params.set('limit', String(filters.limit))
  const qs = params.toString()
  return apiFetch<AuditLogRead[]>(`/api/audit-logs${qs ? `?${qs}` : ''}`)
}
