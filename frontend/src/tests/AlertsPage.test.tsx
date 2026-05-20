import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { AlertsPage } from '../pages/AlertsPage'

vi.mock('../hooks/useAlerts', () => ({
  useAlerts: vi.fn(),
  useResolveAlert: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useAcknowledgeAlert: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useAlerts } from '../hooks/useAlerts'

const mockAlerts = [
  {
    id: 'alert-001',
    title: 'Job "Scraper" failed',
    message: 'Connection timeout',
    severity: 'error',
    source_type: 'job_execution',
    source_id: 'exec-111',
    status: 'open',
    created_at: '2026-05-19T10:00:00Z',
    acknowledged_at: null,
    resolved_at: null,
  },
  {
    id: 'alert-002',
    title: 'Job "Notifier" failed',
    message: 'HTTP 500',
    severity: 'warning',
    source_type: 'job_execution',
    source_id: 'exec-222',
    status: 'resolved',
    created_at: '2026-05-19T09:00:00Z',
    acknowledged_at: null,
    resolved_at: '2026-05-19T09:30:00Z',
  },
]

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<AlertsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('AlertsPage', () => {
  beforeEach(() => {
    vi.mocked(useAlerts).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useAlerts>)
  })

  it('renders the Alerts heading', () => {
    renderPage()
    expect(screen.getByText('Alerts')).toBeInTheDocument()
  })

  it('shows loading text while fetching', () => {
    renderPage()
    expect(screen.getByText('Loading alerts…')).toBeInTheDocument()
  })

  it('shows error message when fetch fails', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useAlerts>)
    renderPage()
    expect(screen.getByText(/Could not load alerts/)).toBeInTheDocument()
  })

  it('shows empty state when no alerts exist', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAlerts>)
    renderPage()
    expect(screen.getByText('No alerts found.')).toBeInTheDocument()
  })

  it('renders alert titles', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: mockAlerts,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAlerts>)
    renderPage()
    expect(screen.getByText('Job "Scraper" failed')).toBeInTheDocument()
    expect(screen.getByText('Job "Notifier" failed')).toBeInTheDocument()
  })

  it('renders severity pills', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: mockAlerts,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAlerts>)
    renderPage()
    expect(screen.getByText('error')).toBeInTheDocument()
    expect(screen.getByText('warning')).toBeInTheDocument()
  })

  it('renders status pills', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: mockAlerts,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAlerts>)
    renderPage()
    expect(screen.getAllByText('Open').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Resolved').length).toBeGreaterThanOrEqual(1)
  })

  it('shows Resolve button only for non-resolved alerts', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: mockAlerts,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAlerts>)
    renderPage()
    expect(screen.getAllByText('Resolve')).toHaveLength(1)
  })

  it('renders filter buttons', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: mockAlerts,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAlerts>)
    renderPage()
    expect(screen.getByText('All')).toBeInTheDocument()
    expect(screen.getAllByText('Open').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Acknowledged')).toBeInTheDocument()
  })
})
