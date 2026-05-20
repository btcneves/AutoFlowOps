import { apiFetch } from './client'
import type {
  EscalationPolicyPayload,
  EscalationPolicyRead,
  EscalationStepPayload,
  EscalationStepRead,
} from '../types'

export function getEscalationPolicies(): Promise<EscalationPolicyRead[]> {
  return apiFetch<EscalationPolicyRead[]>('/api/escalation-policies')
}

export function createEscalationPolicy(
  payload: EscalationPolicyPayload
): Promise<EscalationPolicyRead> {
  return apiFetch<EscalationPolicyRead>('/api/escalation-policies', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateEscalationPolicy({
  id,
  payload,
}: {
  id: string
  payload: Partial<EscalationPolicyPayload>
}): Promise<EscalationPolicyRead> {
  return apiFetch<EscalationPolicyRead>(`/api/escalation-policies/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteEscalationPolicy(id: string): Promise<void> {
  return apiFetch<void>(`/api/escalation-policies/${id}`, { method: 'DELETE' })
}

export function addEscalationStep({
  policyId,
  payload,
}: {
  policyId: string
  payload: EscalationStepPayload
}): Promise<EscalationStepRead> {
  return apiFetch<EscalationStepRead>(`/api/escalation-policies/${policyId}/steps`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteEscalationStep({
  policyId,
  stepId,
}: {
  policyId: string
  stepId: string
}): Promise<void> {
  return apiFetch<void>(`/api/escalation-policies/${policyId}/steps/${stepId}`, {
    method: 'DELETE',
  })
}
