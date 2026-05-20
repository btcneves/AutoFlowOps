import { apiFetch } from './client'
import type { UserCreatePayload, UserRead, UserUpdatePayload } from '../types'

export function getUsers(): Promise<UserRead[]> {
  return apiFetch<UserRead[]>('/api/users')
}

export function createUser(payload: UserCreatePayload): Promise<UserRead> {
  return apiFetch<UserRead>('/api/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateUser(id: string, payload: UserUpdatePayload): Promise<UserRead> {
  return apiFetch<UserRead>(`/api/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function resetPassword(id: string, newPassword: string): Promise<{ detail: string }> {
  return apiFetch<{ detail: string }>(`/api/users/${id}/reset-password`, {
    method: 'POST',
    body: JSON.stringify({ new_password: newPassword }),
  })
}

export function deleteUser(id: string): Promise<void> {
  return apiFetch<void>(`/api/users/${id}`, { method: 'DELETE' })
}
