import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  addEscalationStep,
  createEscalationPolicy,
  deleteEscalationPolicy,
  deleteEscalationStep,
  getEscalationPolicies,
  updateEscalationPolicy,
} from '../api/escalation'

export function useEscalationPolicies() {
  return useQuery({
    queryKey: ['escalation-policies'],
    queryFn: getEscalationPolicies,
  })
}

export function useCreateEscalationPolicy() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: createEscalationPolicy,
    onSuccess: () => client.invalidateQueries({ queryKey: ['escalation-policies'] }),
  })
}

export function useUpdateEscalationPolicy() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: updateEscalationPolicy,
    onSuccess: () => client.invalidateQueries({ queryKey: ['escalation-policies'] }),
  })
}

export function useDeleteEscalationPolicy() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: deleteEscalationPolicy,
    onSuccess: () => client.invalidateQueries({ queryKey: ['escalation-policies'] }),
  })
}

export function useAddEscalationStep() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: addEscalationStep,
    onSuccess: () => client.invalidateQueries({ queryKey: ['escalation-policies'] }),
  })
}

export function useDeleteEscalationStep() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: deleteEscalationStep,
    onSuccess: () => client.invalidateQueries({ queryKey: ['escalation-policies'] }),
  })
}
