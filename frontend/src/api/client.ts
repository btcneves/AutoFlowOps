const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

function getToken(): string | null {
  return localStorage.getItem('access_token')
}

function getActiveWorkspaceId(): string | null {
  return localStorage.getItem('active_workspace_id')
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const wsId = getActiveWorkspaceId()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (wsId) headers['X-Workspace-ID'] = wsId
  if (init?.headers) {
    const extra = init.headers as Record<string, string>
    Object.assign(headers, extra)
  }
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
  })
  if (response.status === 401 || response.status === 403) {
    if (response.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    const detail = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(detail?.detail ?? `HTTP ${response.status}`)
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(detail?.detail ?? `API error ${response.status}: ${response.statusText}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}
