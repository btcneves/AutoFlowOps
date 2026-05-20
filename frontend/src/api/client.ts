const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

function getToken(): string | null {
  return localStorage.getItem('access_token')
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
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
  return response.json() as Promise<T>
}
