import { apiFetch } from './client'
import type { LoginRequest, TokenResponse, UserRead } from '../types'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const response = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: 'Login failed' }))
    throw new Error(detail?.detail ?? 'Login failed')
  }
  return response.json() as Promise<TokenResponse>
}

export function getMe(): Promise<UserRead> {
  return apiFetch<UserRead>('/api/auth/me')
}
