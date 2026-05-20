import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NotificationChannelsPage } from '../pages/NotificationChannelsPage'

vi.mock('../hooks/useNotifications', () => ({
  useNotificationChannels: vi.fn(),
  useNotificationDeliveries: vi.fn(),
  useCreateNotificationChannel: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateNotificationChannel: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteNotificationChannel: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useActivateNotificationChannel: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeactivateNotificationChannel: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useTestNotificationChannel: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import {
  useNotificationChannels,
  useNotificationDeliveries,
} from '../hooks/useNotifications'

const mockChannels = [
  {
    id: 'channel-001',
    name: 'Ops Discord',
    type: 'discord_webhook',
    status: 'active',
    config_masked: { webhook_url: 'https://discord.com/***' },
    created_at: '2026-05-20T10:00:00Z',
    updated_at: '2026-05-20T10:00:00Z',
    last_tested_at: null,
  },
]

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <NotificationChannelsPage />
    </QueryClientProvider>
  )
}

describe('NotificationChannelsPage', () => {
  beforeEach(() => {
    vi.mocked(useNotificationChannels).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useNotificationChannels>)
    vi.mocked(useNotificationDeliveries).mockReturnValue({
      data: [],
    } as unknown as ReturnType<typeof useNotificationDeliveries>)
  })

  it('renders the page heading', () => {
    renderPage()
    expect(screen.getByText('Notification Channels')).toBeInTheDocument()
  })

  it('shows loading text while fetching channels', () => {
    renderPage()
    expect(screen.getByText('Loading channels…')).toBeInTheDocument()
  })

  it('shows empty state when no channels exist', () => {
    vi.mocked(useNotificationChannels).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useNotificationChannels>)
    renderPage()
    expect(screen.getByText('No notification channels configured yet.')).toBeInTheDocument()
  })

  it('renders configured channels and actions', () => {
    vi.mocked(useNotificationChannels).mockReturnValue({
      data: mockChannels,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useNotificationChannels>)
    renderPage()
    expect(screen.getByText('Ops Discord')).toBeInTheDocument()
    expect(screen.getAllByText('Discord webhook').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Test')).toBeInTheDocument()
    expect(screen.getByText('Pause')).toBeInTheDocument()
  })
})
