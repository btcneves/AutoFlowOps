import { apiFetch } from './client'
import type {
  WorkspaceCreate,
  WorkspaceMemberCreate,
  WorkspaceMemberRead,
  WorkspaceRead,
  WorkspaceUpdate,
} from '../types'

export function listWorkspaces(): Promise<WorkspaceRead[]> {
  return apiFetch<WorkspaceRead[]>('/api/workspaces')
}

export function createWorkspace(payload: WorkspaceCreate): Promise<WorkspaceRead> {
  return apiFetch<WorkspaceRead>('/api/workspaces', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateWorkspace(id: string, payload: WorkspaceUpdate): Promise<WorkspaceRead> {
  return apiFetch<WorkspaceRead>(`/api/workspaces/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteWorkspace(id: string): Promise<void> {
  return apiFetch<void>(`/api/workspaces/${id}`, { method: 'DELETE' })
}

export function listMembers(workspaceId: string): Promise<WorkspaceMemberRead[]> {
  return apiFetch<WorkspaceMemberRead[]>(`/api/workspaces/${workspaceId}/members`)
}

export function addMember(
  workspaceId: string,
  payload: WorkspaceMemberCreate,
): Promise<WorkspaceMemberRead> {
  return apiFetch<WorkspaceMemberRead>(`/api/workspaces/${workspaceId}/members`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function removeMember(workspaceId: string, userId: string): Promise<void> {
  return apiFetch<void>(`/api/workspaces/${workspaceId}/members/${userId}`, {
    method: 'DELETE',
  })
}
