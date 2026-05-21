import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { JobDetailPage } from '../pages/JobDetailPage'

vi.mock('../hooks/useJobs', () => ({
  useJob: vi.fn(),
  useRunJob: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUpdateJob: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteJob: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}))

vi.mock('../hooks/useExecutions', () => ({
  useExecutions: vi.fn(),
}))

vi.mock('../hooks/useAlertRules', () => ({
  useAlertRules: vi.fn(),
  useCreateAlertRule: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateAlertRule: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteAlertRule: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({ isOperator: true })),
}))

import { useExecutions } from '../hooks/useExecutions'
import { useAlertRules } from '../hooks/useAlertRules'
import { useJob } from '../hooks/useJobs'

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

const SAMPLE_RULE = {
  id: 'rule-001',
  job_id: SAMPLE_JOB.id,
  condition_type: 'http_status_gte',
  condition_value: '500',
  severity: 'error',
  message: 'Backend is failing',
  is_enabled: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={[`/jobs/${SAMPLE_JOB.id}`]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/jobs/:id" element={<JobDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('JobDetailPage', () => {
  beforeEach(() => {
    vi.mocked(useJob).mockReturnValue({
      data: SAMPLE_JOB,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useJob>)
    vi.mocked(useExecutions).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useExecutions>)
    vi.mocked(useAlertRules).mockReturnValue({
      data: [SAMPLE_RULE],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAlertRules>)
  })

  it('renders alert rules on the job detail page', () => {
    renderPage()

    expect(screen.getByText('Alert Rules')).toBeInTheDocument()
    expect(screen.getAllByText('HTTP status >=').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('500')).toBeInTheDocument()
    expect(screen.getByText('Backend is failing')).toBeInTheDocument()
    expect(screen.getByText('Enabled')).toBeInTheDocument()
  })
})
