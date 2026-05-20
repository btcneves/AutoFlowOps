import { apiFetch } from './client'
import type { AlertRead } from '../types'

export function getAlerts(status?: string): Promise<AlertRead[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ''
  return apiFetch<AlertRead[]>(`/api/alerts${qs}`)
}

export function resolveAlert(alertId: string): Promise<AlertRead> {
  return apiFetch<AlertRead>(`/api/alerts/${alertId}/resolve`, { method: 'PATCH' })
}

export function acknowledgeAlert(alertId: string): Promise<AlertRead> {
  return apiFetch<AlertRead>(`/api/alerts/${alertId}/acknowledge`, { method: 'PATCH' })
}
