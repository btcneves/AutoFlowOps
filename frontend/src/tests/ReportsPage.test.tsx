import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { downloadReport } from '../api/reports'
import { useGenerateReport, useReports } from '../hooks/useReports'
import { ReportsPage } from '../pages/ReportsPage'

vi.mock('../hooks/useReports', () => ({
  useReports: vi.fn(),
  useGenerateReport: vi.fn(),
}))

vi.mock('../api/reports', () => ({
  downloadReport: vi.fn(),
}))

const mockReports = [
  {
    id: 'report-001',
    name: 'Weekly Ops',
    format: 'json',
    period_start: '2026-05-12T10:00:00Z',
    period_end: '2026-05-19T10:00:00Z',
    created_at: '2026-05-19T10:30:00Z',
    created_by: null,
  },
]

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<ReportsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ReportsPage', () => {
  const mutate = vi.fn()

  beforeEach(() => {
    mutate.mockReset()
    vi.mocked(downloadReport).mockReset()
    vi.mocked(downloadReport).mockResolvedValue(undefined)
    vi.mocked(useGenerateReport).mockReturnValue({
      mutate,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useGenerateReport>)
    vi.mocked(useReports).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useReports>)
  })

  it('renders the Reports heading', () => {
    renderPage()
    expect(screen.getByText('Reports')).toBeInTheDocument()
  })

  it('shows loading text while fetching', () => {
    renderPage()
    expect(screen.getByText('Loading reports…')).toBeInTheDocument()
  })

  it('shows error message when fetch fails', () => {
    vi.mocked(useReports).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useReports>)
    renderPage()
    expect(screen.getByText(/Could not load reports/)).toBeInTheDocument()
  })

  it('shows empty state when no reports exist', () => {
    vi.mocked(useReports).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useReports>)
    renderPage()
    expect(screen.getByText('No reports generated yet.')).toBeInTheDocument()
  })

  it('generates a report for the selected period', async () => {
    const user = userEvent.setup()
    vi.mocked(useReports).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useReports>)
    renderPage()

    await user.type(screen.getByLabelText('Name'), 'Ops Snapshot')
    await user.click(screen.getByRole('button', { name: 'Generate Report' }))

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Ops Snapshot',
        period_start: expect.any(String),
        period_end: expect.any(String),
      })
    )
  })

  it('renders report rows and download buttons', () => {
    vi.mocked(useReports).mockReturnValue({
      data: mockReports,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useReports>)
    renderPage()

    expect(screen.getByText('Weekly Ops')).toBeInTheDocument()
    expect(screen.getByText('json')).toBeInTheDocument()
    expect(screen.getByText('JSON')).toBeInTheDocument()
    expect(screen.getByText('Markdown')).toBeInTheDocument()
    expect(screen.getByText('CSV')).toBeInTheDocument()
  })

  it('downloads report formats', async () => {
    const user = userEvent.setup()
    vi.mocked(useReports).mockReturnValue({
      data: mockReports,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useReports>)
    renderPage()

    await user.click(screen.getByRole('button', { name: 'JSON' }))

    expect(downloadReport).toHaveBeenCalledWith('report-001', 'json')
  })
})
