import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useWebSocket } from '../hooks/useWebSocket'

// ---------------------------------------------------------------------------
// Mock WebSocket
// ---------------------------------------------------------------------------

interface MockCloseEvent {
  code: number
}
interface MockMessageEvent {
  data: string
}

class MockWebSocket {
  url: string
  onopen: (() => void) | null = null
  onmessage: ((e: MockMessageEvent) => void) | null = null
  onclose: ((e: MockCloseEvent) => void) | null = null
  onerror: (() => void) | null = null

  static instances: MockWebSocket[] = []

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send(_data: string): void {}

  close(code = 1000): void {
    this.onclose?.({ code })
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    localStorage.setItem('access_token', 'fake-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
    localStorage.clear()
  })

  it('creates a WebSocket connection on mount', () => {
    renderHook(() => useWebSocket())
    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it('starts with connecting status', () => {
    const { result } = renderHook(() => useWebSocket())
    expect(result.current.status).toBe('connecting')
  })

  it('sets auth_error when no token is present', () => {
    localStorage.clear()
    const { result } = renderHook(() => useWebSocket())
    expect(result.current.status).toBe('auth_error')
    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('transitions to open on successful connection', () => {
    const { result } = renderHook(() => useWebSocket())
    act(() => {
      MockWebSocket.instances[0].onopen?.()
    })
    expect(result.current.status).toBe('open')
  })

  it('sets lastEvent when a message arrives', () => {
    const { result } = renderHook(() => useWebSocket())
    const event = { type: 'execution.completed', data: { execution_id: '123' }, ts: '2026-05-20T00:00:00Z' }
    act(() => {
      MockWebSocket.instances[0].onmessage?.({ data: JSON.stringify(event) })
    })
    expect(result.current.lastEvent?.type).toBe('execution.completed')
    expect(result.current.lastEvent?.data).toEqual({ execution_id: '123' })
  })

  it('ignores pong messages (does not update lastEvent)', () => {
    const { result } = renderHook(() => useWebSocket())
    act(() => {
      MockWebSocket.instances[0].onmessage?.({ data: JSON.stringify({ type: 'pong' }) })
    })
    expect(result.current.lastEvent).toBeNull()
  })

  it('ignores connected messages (does not update lastEvent)', () => {
    const { result } = renderHook(() => useWebSocket())
    act(() => {
      MockWebSocket.instances[0].onmessage?.({ data: JSON.stringify({ type: 'connected', data: {} }) })
    })
    expect(result.current.lastEvent).toBeNull()
  })

  it('sets auth_error on close code 1008 and does not reconnect', () => {
    const { result } = renderHook(() => useWebSocket())
    act(() => {
      MockWebSocket.instances[0].onclose?.({ code: 1008 })
    })
    expect(result.current.status).toBe('auth_error')
    act(() => {
      vi.advanceTimersByTime(10_000)
    })
    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it('schedules reconnect on non-auth close', () => {
    renderHook(() => useWebSocket())
    act(() => {
      MockWebSocket.instances[0].onclose?.({ code: 1006 })
    })
    act(() => {
      vi.advanceTimersByTime(1_500)
    })
    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('closes the socket on unmount', () => {
    const closeSpy = vi.fn()
    const { unmount } = renderHook(() => useWebSocket())
    const ws = MockWebSocket.instances[0]
    ws.close = closeSpy
    unmount()
    expect(closeSpy).toHaveBeenCalled()
  })
})
