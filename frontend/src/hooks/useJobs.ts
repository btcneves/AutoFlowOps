import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createJob, deleteJob, getJob, getJobs, runJob, updateJob } from '../api/jobs'
import type { JobCreate, JobUpdate } from '../types'

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: getJobs,
    refetchInterval: 30_000,
  })
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ['jobs', id],
    queryFn: () => getJob(id),
  })
}

export function useCreateJob() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (payload: JobCreate) => createJob(payload),
    onSuccess: () => client.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useUpdateJob(id: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (payload: JobUpdate) => updateJob(id, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['jobs'] })
      client.invalidateQueries({ queryKey: ['jobs', id] })
    },
  })
}

export function useDeleteJob() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteJob(id),
    onSuccess: () => client.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useRunJob() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => runJob(id),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['jobs'] })
      client.invalidateQueries({ queryKey: ['executions'] })
    },
  })
}
