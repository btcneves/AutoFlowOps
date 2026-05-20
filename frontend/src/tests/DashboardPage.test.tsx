import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { DashboardPage } from '../pages/DashboardPage'

vi.mock('../hooks/useHealth', () => ({
  useHealth: vi.fn(),
}))

vi.mock('../hooks/useStats', () => ({
  useStats: vi.fn(),
}))

import { useHealth } from '../hooks/useHealth'
import { useStats } from '../hooks/useStats'

const defaultStats = {
  total_jobs: 0,
  active_jobs: 0,
  paused_jobs: 0,
  total_executions: 0,
  executions_24h: 0,
  failures_24h: 0,
  success_rate_24h: 0,
  daily_stats: [],
}

function renderDashboard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.mocked(useHealth).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useHealth>)

    vi.mocked(useStats).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useStats>)
  })

  it('renders the Dashboard heading', () => {
    renderDashboard()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('shows checking status badge while loading', () => {
    renderDashboard()
    expect(screen.getByText('Checking…')).toBeInTheDocument()
  })

  it('shows Online badge when backend is healthy', () => {
    vi.mocked(useHealth).mockReturnValue({
      data: { status: 'ok', app: 'AutoFlowOps', env: 'development' },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHealth>)
    renderDashboard()
    expect(screen.getByText('Online')).toBeInTheDocument()
    expect(screen.getByText(/Connected to AutoFlowOps/)).toBeInTheDocument()
  })

  it('shows Error badge and message when backend is unreachable', () => {
    vi.mocked(useHealth).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useHealth>)
    renderDashboard()
    expect(screen.getByText('Error')).toBeInTheDocument()
    expect(screen.getByText(/Could not reach the backend/)).toBeInTheDocument()
  })

  it('renders all four metric cards', () => {
    renderDashboard()
    expect(screen.getByText('Active Jobs')).toBeInTheDocument()
    expect(screen.getByText('Executions (24h)')).toBeInTheDocument()
    expect(screen.getByText('Failures (24h)')).toBeInTheDocument()
    expect(screen.getByText('Success Rate')).toBeInTheDocument()
  })

  it('shows real metrics when stats are loaded', () => {
    vi.mocked(useStats).mockReturnValue({
      data: { ...defaultStats, active_jobs: 3, executions_24h: 12, failures_24h: 1, success_rate_24h: 91.7, total_jobs: 5, total_executions: 42, daily_stats: [] },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStats>)
    renderDashboard()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('91.7%')).toBeInTheDocument()
  })

  it('shows N/A success rate when no executions', () => {
    vi.mocked(useStats).mockReturnValue({
      data: { ...defaultStats },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useStats>)
    renderDashboard()
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })
})
