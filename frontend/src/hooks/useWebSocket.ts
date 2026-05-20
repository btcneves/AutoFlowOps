import { useEffect, useRef, useState } from 'react'

export interface WSEvent {
  type: string
  data: Record<string, unknown>
  ts: string
}

export type WSStatus = 'connecting' | 'open' | 'closed' | 'auth_error'

const MAX_RECONNECT_DELAY_MS = 30_000

function buildWsUrl(): string {
  const apiBase =
    (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'
  return apiBase.replace(/^http/, 'ws') + '/ws/events'
}

export function useWebSocket() {
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null)
  const [status, setStatus] = useState<WSStatus>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const attemptRef = useRef(0)
  const unmountedRef = useRef(false)

  useEffect(() => {
    unmountedRef.current = false

    function connect() {
      if (unmountedRef.current) return

      const token = localStorage.getItem('access_token')
      if (!token) {
        setStatus('auth_error')
        return
      }

      const url = buildWsUrl() + '?token=' + encodeURIComponent(token)
      const ws = new WebSocket(url)
      wsRef.current = ws
      setStatus('connecting')

      ws.onopen = () => {
        setStatus('open')
        attemptRef.current = 0
      }

      ws.onmessage = (e: MessageEvent<string>) => {
        try {
          const event: WSEvent = JSON.parse(e.data) as WSEvent
          if (event.type !== 'pong' && event.type !== 'connected') {
            setLastEvent(event)
          }
        } catch {
          // ignore malformed frames
        }
      }

      ws.onclose = (e: CloseEvent) => {
        if (unmountedRef.current) return
        if (e.code === 1008) {
          // Policy Violation — auth failure; do not reconnect
          setStatus('auth_error')
          return
        }
        setStatus('closed')
        const delay = Math.min(1_000 * Math.pow(2, attemptRef.current), MAX_RECONNECT_DELAY_MS)
        attemptRef.current++
        setTimeout(connect, delay)
      }

      ws.onerror = () => {
        // onclose fires after onerror; no additional action needed
      }
    }

    connect()

    return () => {
      unmountedRef.current = true
      wsRef.current?.close()
    }
  }, [])

  return { lastEvent, status }
}
