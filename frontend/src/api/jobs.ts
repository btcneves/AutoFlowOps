import { apiFetch } from './client'
import type { ExecutionRead, JobCreate, JobRead, JobUpdate } from '../types'

export function getJobs(): Promise<JobRead[]> {
  return apiFetch<JobRead[]>('/api/jobs')
}

export function getJob(id: string): Promise<JobRead> {
  return apiFetch<JobRead>(`/api/jobs/${id}`)
}

export function createJob(payload: JobCreate): Promise<JobRead> {
  return apiFetch<JobRead>('/api/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateJob(id: string, payload: JobUpdate): Promise<JobRead> {
  return apiFetch<JobRead>(`/api/jobs/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteJob(id: string): Promise<void> {
  return apiFetch<void>(`/api/jobs/${id}`, { method: 'DELETE' })
}

export function runJob(id: string): Promise<ExecutionRead> {
  return apiFetch<ExecutionRead>(`/api/jobs/${id}/run`, { method: 'POST' })
}
