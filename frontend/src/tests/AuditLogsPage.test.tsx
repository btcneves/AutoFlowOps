import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuditLogsPage } from '../pages/AuditLogsPage'

vi.mock('../hooks/useAuditLogs', () => ({
  useAuditLogs: vi.fn(),
}))

import { useAuditLogs } from '../hooks/useAuditLogs'

const mockLogs = [
  {
    id: 'log-001',
    user_id: 'user-001',
    action: 'auth.login_success',
    resource_type: null,
    resource_id: null,
    status: 'success',
    ip_address: '127.0.0.1',
    user_agent: 'test',
    metadata_: null,
    created_at: '2026-05-20T10:00:00Z',
  },
]

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AuditLogsPage />
    </QueryClientProvider>
  )
}

describe('AuditLogsPage', () => {
  beforeEach(() => {
    vi.mocked(useAuditLogs).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useAuditLogs>)
  })

  it('renders the page heading', () => {
    renderPage()
    expect(screen.getByText('Audit Logs')).toBeInTheDocument()
  })

  it('shows loading text while fetching', () => {
    renderPage()
    expect(screen.getByText('Loading audit logs…')).toBeInTheDocument()
  })

  it('shows empty state when no logs exist', () => {
    vi.mocked(useAuditLogs).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAuditLogs>)
    renderPage()
    expect(screen.getByText('No audit log entries found.')).toBeInTheDocument()
  })

  it('renders logs in a table', () => {
    vi.mocked(useAuditLogs).mockReturnValue({
      data: mockLogs,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useAuditLogs>)
    renderPage()
    expect(screen.getByText('auth.login_success')).toBeInTheDocument()
    expect(screen.getByText('success')).toBeInTheDocument()
    expect(screen.getByText('127.0.0.1')).toBeInTheDocument()
  })
})
