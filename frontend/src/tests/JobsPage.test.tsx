import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { JobsPage } from '../pages/JobsPage'

vi.mock('../hooks/useJobs', () => ({
  useJobs: vi.fn(),
  useRunJob: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteJob: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useJobs } from '../hooks/useJobs'

const SAMPLE_JOB = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  name: 'Health Check',
  description: 'Daily API health check',
  type: 'http',
  status: 'active',
  schedule_type: 'interval',
  schedule_expression: '300',
  method: 'GET',
  url: 'https://api.example.com/health',
  headers_masked: null,
  timeout_seconds: 30,
  retry_count: 0,
  retry_delay_seconds: 60,
  alert_on_failure: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  last_run_at: null,
  next_run_at: null,
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<JobsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('JobsPage', () => {
  beforeEach(() => {
    vi.mocked(useJobs).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useJobs>)
  })

  it('renders the Jobs heading', () => {
    renderPage()
    expect(screen.getByText('Jobs')).toBeInTheDocument()
  })

  it('shows New Job link', () => {
    renderPage()
    expect(screen.getByText('New Job')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    renderPage()
    expect(screen.getByText('Loading jobs…')).toBeInTheDocument()
  })

  it('shows empty state when no jobs', () => {
    vi.mocked(useJobs).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useJobs>)
    renderPage()
    expect(screen.getByText('No jobs yet.')).toBeInTheDocument()
  })

  it('renders a job row when jobs exist', () => {
    vi.mocked(useJobs).mockReturnValue({
      data: [SAMPLE_JOB],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useJobs>)
    renderPage()
    expect(screen.getByText('Health Check')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('shows error when API fails', () => {
    vi.mocked(useJobs).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useJobs>)
    renderPage()
    expect(screen.getByText(/Could not load jobs/)).toBeInTheDocument()
  })
})
