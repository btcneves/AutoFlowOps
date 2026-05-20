import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { WebhooksPage } from '../pages/WebhooksPage'

vi.mock('../hooks/useWebhooks', () => ({
  useWebhooks: vi.fn(),
}))

import { useWebhooks } from '../hooks/useWebhooks'

const mockWebhooks = [
  {
    id: 'aaaa-1111',
    name: 'Order Events',
    slug: 'order-events',
    status: 'active',
    created_at: '2026-05-19T10:00:00Z',
    updated_at: '2026-05-19T10:00:00Z',
    last_received_at: '2026-05-19T12:30:00Z',
  },
  {
    id: 'bbbb-2222',
    name: 'Payment Hook',
    slug: 'payment-hook',
    status: 'paused',
    created_at: '2026-05-19T09:00:00Z',
    updated_at: '2026-05-19T09:00:00Z',
    last_received_at: null,
  },
]

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<WebhooksPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('WebhooksPage', () => {
  beforeEach(() => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useWebhooks>)
  })

  it('renders the Webhooks heading', () => {
    renderPage()
    expect(screen.getByText('Webhooks')).toBeInTheDocument()
  })

  it('shows loading text while fetching', () => {
    renderPage()
    expect(screen.getByText('Loading webhooks…')).toBeInTheDocument()
  })

  it('shows error message when fetch fails', () => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useWebhooks>)
    renderPage()
    expect(screen.getByText(/Could not load webhooks/)).toBeInTheDocument()
  })

  it('shows empty state when no webhooks exist', () => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useWebhooks>)
    renderPage()
    expect(screen.getByText('No webhooks configured yet.')).toBeInTheDocument()
  })

  it('renders webhook names and slugs', () => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: mockWebhooks,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useWebhooks>)
    renderPage()
    expect(screen.getByText('Order Events')).toBeInTheDocument()
    expect(screen.getByText('Payment Hook')).toBeInTheDocument()
    expect(screen.getByText('order-events')).toBeInTheDocument()
    expect(screen.getByText('payment-hook')).toBeInTheDocument()
  })

  it('shows Active and Paused status pills', () => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: mockWebhooks,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useWebhooks>)
    renderPage()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('Paused')).toBeInTheDocument()
  })

  it('shows em-dash for null last_received_at', () => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: mockWebhooks,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useWebhooks>)
    renderPage()
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1)
  })

  it('renders Copy URL buttons for each webhook', () => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: mockWebhooks,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useWebhooks>)
    renderPage()
    expect(screen.getAllByText('Copy URL')).toHaveLength(2)
  })
})
