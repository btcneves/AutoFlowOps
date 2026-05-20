import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NotificationTemplatesPage } from '../pages/NotificationTemplatesPage'

vi.mock('../hooks/useNotificationTemplates', () => ({
  useNotificationTemplates: vi.fn(),
  useCreateNotificationTemplate: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateNotificationTemplate: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteNotificationTemplate: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useNotificationTemplates } from '../hooks/useNotificationTemplates'

const mockTemplates = [
  {
    id: 'tmpl-001',
    name: 'Error template',
    severity_filter: 'error',
    title_template: 'CRITICAL: {title}',
    body_template: '{title}\n{message}',
    is_default: false,
    created_at: '2026-05-20T10:00:00Z',
    updated_at: '2026-05-20T10:00:00Z',
  },
]

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <NotificationTemplatesPage />
    </QueryClientProvider>
  )
}

describe('NotificationTemplatesPage', () => {
  beforeEach(() => {
    vi.mocked(useNotificationTemplates).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useNotificationTemplates>)
  })

  it('renders the page heading', () => {
    renderPage()
    expect(screen.getByText('Notification Templates')).toBeInTheDocument()
  })

  it('shows loading text while fetching', () => {
    renderPage()
    expect(screen.getByText('Loading templates…')).toBeInTheDocument()
  })

  it('shows empty state when no templates exist', () => {
    vi.mocked(useNotificationTemplates).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useNotificationTemplates>)
    renderPage()
    expect(screen.getByText(/No templates configured/)).toBeInTheDocument()
  })

  it('renders templates in a table', () => {
    vi.mocked(useNotificationTemplates).mockReturnValue({
      data: mockTemplates,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useNotificationTemplates>)
    renderPage()
    expect(screen.getByText('Error template')).toBeInTheDocument()
    expect(screen.getByText('CRITICAL: {title}')).toBeInTheDocument()
    expect(screen.getAllByText('error').length).toBeGreaterThanOrEqual(1)
  })
})
