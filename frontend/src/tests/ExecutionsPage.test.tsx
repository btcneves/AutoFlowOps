import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { ExecutionsPage } from '../pages/ExecutionsPage'

vi.mock('../hooks/useExecutions', () => ({
  useExecutions: vi.fn(),
}))

vi.mock('../hooks/useJobs', () => ({
  useJobs: vi.fn(() => ({ data: [], isLoading: false, isError: false })),
  useRunJob: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteJob: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useExecutions } from '../hooks/useExecutions'

const SAMPLE_EXECUTION = {
  id: 'exec-1',
  job_id: 'job-1',
  trigger_type: 'manual',
  status: 'success',
  started_at: '2026-01-01T10:00:00Z',
  finished_at: '2026-01-01T10:00:01Z',
  duration_ms: 1000,
  request_method: 'GET',
  request_url: 'https://example.com',
  request_headers_masked: null,
  request_body_masked: null,
  response_status_code: 200,
  response_body_preview: 'OK',
  error_message: null,
  retry_attempt: 0,
  created_at: '2026-01-01T10:00:00Z',
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<ExecutionsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ExecutionsPage', () => {
  beforeEach(() => {
    vi.mocked(useExecutions).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useExecutions>)
  })

  it('renders the Executions heading', () => {
    renderPage()
    expect(screen.getByText('Executions')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    renderPage()
    expect(screen.getByText('Loading executions…')).toBeInTheDocument()
  })

  it('shows empty state when no executions', () => {
    vi.mocked(useExecutions).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useExecutions>)
    renderPage()
    expect(screen.getByText('No executions found.')).toBeInTheDocument()
  })

  it('renders an execution row when executions exist', () => {
    vi.mocked(useExecutions).mockReturnValue({
      data: [SAMPLE_EXECUTION],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useExecutions>)
    renderPage()
    expect(screen.getAllByText('Success').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('1000 ms')).toBeInTheDocument()
  })

  it('shows error when API fails', () => {
    vi.mocked(useExecutions).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useExecutions>)
    renderPage()
    expect(screen.getByText(/Could not load executions/)).toBeInTheDocument()
  })

  it('renders status filter buttons', () => {
    renderPage()
    expect(screen.getByText('All')).toBeInTheDocument()
    expect(screen.getByText('Success')).toBeInTheDocument()
    expect(screen.getByText('Failure')).toBeInTheDocument()
  })
})
