import { apiFetch } from './client'
import type { AlertRuleCreate, AlertRuleRead, AlertRuleUpdate } from '../types'

export function getAlertRules(jobId: string): Promise<AlertRuleRead[]> {
  return apiFetch<AlertRuleRead[]>(`/api/jobs/${jobId}/alert-rules`)
}

export function createAlertRule(
  jobId: string,
  payload: AlertRuleCreate,
): Promise<AlertRuleRead> {
  return apiFetch<AlertRuleRead>(`/api/jobs/${jobId}/alert-rules`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateAlertRule(
  jobId: string,
  ruleId: string,
  payload: AlertRuleUpdate,
): Promise<AlertRuleRead> {
  return apiFetch<AlertRuleRead>(`/api/jobs/${jobId}/alert-rules/${ruleId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteAlertRule(jobId: string, ruleId: string): Promise<void> {
  return apiFetch<void>(`/api/jobs/${jobId}/alert-rules/${ruleId}`, {
    method: 'DELETE',
  })
}
