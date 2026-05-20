import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EscalationPoliciesPage } from '../pages/EscalationPoliciesPage'

vi.mock('../hooks/useEscalation', () => ({
  useEscalationPolicies: vi.fn(),
  useCreateEscalationPolicy: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateEscalationPolicy: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteEscalationPolicy: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useAddEscalationStep: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteEscalationStep: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

vi.mock('../hooks/useNotifications', () => ({
  useNotificationChannels: vi.fn(() => ({ data: [] })),
}))

import { useEscalationPolicies } from '../hooks/useEscalation'

const mockPolicies = [
  {
    id: 'policy-001',
    name: 'Ops escalation',
    is_active: true,
    steps: [
      {
        id: 'step-001',
        policy_id: 'policy-001',
        step_order: 0,
        channel_id: 'ch-001',
        delay_minutes: 0,
      },
      {
        id: 'step-002',
        policy_id: 'policy-001',
        step_order: 1,
        channel_id: 'ch-002',
        delay_minutes: 30,
      },
    ],
    created_at: '2026-05-20T10:00:00Z',
    updated_at: '2026-05-20T10:00:00Z',
  },
]

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <EscalationPoliciesPage />
    </QueryClientProvider>
  )
}

describe('EscalationPoliciesPage', () => {
  beforeEach(() => {
    vi.mocked(useEscalationPolicies).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useEscalationPolicies>)
  })

  it('renders the page heading', () => {
    renderPage()
    expect(screen.getByText('Escalation Policies')).toBeInTheDocument()
  })

  it('shows loading text while fetching', () => {
    renderPage()
    expect(screen.getByText('Loading policies…')).toBeInTheDocument()
  })

  it('shows empty state when no policies exist', () => {
    vi.mocked(useEscalationPolicies).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useEscalationPolicies>)
    renderPage()
    expect(screen.getByText('No escalation policies configured yet.')).toBeInTheDocument()
  })

  it('renders policies in a table', () => {
    vi.mocked(useEscalationPolicies).mockReturnValue({
      data: mockPolicies,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useEscalationPolicies>)
    renderPage()
    expect(screen.getByText('Ops escalation')).toBeInTheDocument()
    expect(screen.getAllByText('Active').length).toBeGreaterThanOrEqual(1)
  })
})
