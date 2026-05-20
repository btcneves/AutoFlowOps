import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UsersPage } from '../pages/UsersPage'

vi.mock('../hooks/useUsers', () => ({
  useUsers: vi.fn(),
  useCreateUser: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateUser: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useResetPassword: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteUser: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

import { useUsers } from '../hooks/useUsers'

const mockUsers = [
  {
    id: 'user-001',
    email: 'admin@autoflowops.local',
    name: 'Admin',
    role: 'admin',
    is_active: true,
    created_at: '2026-05-20T10:00:00Z',
    updated_at: '2026-05-20T10:00:00Z',
    last_login_at: '2026-05-20T11:00:00Z',
  },
]

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <UsersPage />
    </QueryClientProvider>
  )
}

describe('UsersPage', () => {
  beforeEach(() => {
    vi.mocked(useUsers).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useUsers>)
  })

  it('renders the page heading', () => {
    renderPage()
    expect(screen.getByText('Users')).toBeInTheDocument()
  })

  it('shows loading text while fetching', () => {
    renderPage()
    expect(screen.getByText('Loading users…')).toBeInTheDocument()
  })

  it('shows empty state when no users exist', () => {
    vi.mocked(useUsers).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useUsers>)
    renderPage()
    expect(screen.getByText('No users found.')).toBeInTheDocument()
  })

  it('renders users in a table', () => {
    vi.mocked(useUsers).mockReturnValue({
      data: mockUsers,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useUsers>)
    renderPage()
    expect(screen.getByText('admin@autoflowops.local')).toBeInTheDocument()
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })
})
