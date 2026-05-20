import { FormEvent, useState } from 'react'
import {
  useCreateUser,
  useDeleteUser,
  useResetPassword,
  useUpdateUser,
  useUsers,
} from '../hooks/useUsers'
import type { UserRead, UserRole } from '../types'

const ROLE_OPTIONS: UserRole[] = ['admin', 'operator', 'viewer']

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function UserForm({ onDone }: { onDone: () => void }) {
  const create = useCreateUser()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('viewer')
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!email.trim() || !name.trim() || !password) {
      setError('Email, name and password are required.')
      return
    }
    try {
      await create.mutateAsync({ email: email.trim(), name: name.trim(), password, role })
      onDone()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <h2 className="mb-3 text-sm font-semibold text-gray-900">New user</h2>
      <div className="grid gap-3 md:grid-cols-4">
        <label className="text-xs font-medium text-gray-600">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs font-medium text-gray-600">
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs font-medium text-gray-600">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs font-medium text-gray-600">
          Role
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      <button
        disabled={create.isPending}
        className="mt-3 rounded bg-gray-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
      >
        Create user
      </button>
    </form>
  )
}

function UserRow({
  user,
  currentUserId,
}: {
  user: UserRead
  currentUserId: string | undefined
}) {
  const updateUser = useUpdateUser()
  const deleteUser = useDeleteUser()
  const resetPassword = useResetPassword()
  const [editRole, setEditRole] = useState<string>(user.role)
  const [showReset, setShowReset] = useState(false)
  const [newPw, setNewPw] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)

  const isSelf = user.id === currentUserId

  async function handleRoleChange(role: string) {
    setEditRole(role)
    await updateUser.mutateAsync({ id: user.id, payload: { role: role as UserRole } })
  }

  async function handleToggleActive() {
    await updateUser.mutateAsync({
      id: user.id,
      payload: { is_active: !user.is_active },
    })
  }

  async function handleResetPw(e: FormEvent) {
    e.preventDefault()
    setPwError(null)
    if (!newPw || newPw.length < 6) {
      setPwError('Password must be at least 6 characters.')
      return
    }
    try {
      await resetPassword.mutateAsync({ id: user.id, password: newPw })
      setShowReset(false)
      setNewPw('')
    } catch (err) {
      setPwError((err as Error).message)
    }
  }

  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{user.name}</td>
      <td className="py-3 pr-4 text-xs text-gray-600">{user.email}</td>
      <td className="py-3 pr-4">
        <select
          value={editRole}
          onChange={(e) => handleRoleChange(e.target.value)}
          disabled={isSelf || updateUser.isPending}
          className="rounded border border-gray-300 px-1 py-0.5 text-xs disabled:opacity-50"
        >
          {ROLE_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </td>
      <td className="py-3 pr-4 text-xs">
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}
        >
          {user.is_active ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(user.last_login_at)}</td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(user.created_at)}</td>
      <td className="py-3 pr-4 text-right space-x-1">
        <button
          onClick={handleToggleActive}
          disabled={isSelf || updateUser.isPending}
          className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          {user.is_active ? 'Deactivate' : 'Activate'}
        </button>
        <button
          onClick={() => setShowReset(!showReset)}
          className="rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50"
        >
          Reset pw
        </button>
        <button
          onClick={() => deleteUser.mutate(user.id)}
          disabled={isSelf || deleteUser.isPending}
          className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
        >
          Delete
        </button>
      </td>
      {showReset && (
        <td colSpan={7} className="py-2 pl-4">
          <form onSubmit={handleResetPw} className="flex items-center gap-2">
            <input
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="New password"
              className="rounded border border-gray-300 px-2 py-1 text-xs"
            />
            <button
              type="submit"
              disabled={resetPassword.isPending}
              className="rounded bg-blue-600 px-2 py-1 text-xs text-white disabled:opacity-50"
            >
              Set
            </button>
            {pwError && <span className="text-xs text-red-600">{pwError}</span>}
          </form>
        </td>
      )}
    </tr>
  )
}

export function UsersPage() {
  const { data: users, isLoading, isError } = useUsers()
  const [showForm, setShowForm] = useState(false)

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage user accounts and role assignments.
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-700"
        >
          {showForm ? 'Cancel' : 'New user'}
        </button>
      </div>

      {showForm && <UserForm onDone={() => setShowForm(false)} />}

      {isLoading && <p className="text-sm text-gray-500">Loading users…</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not load users.
        </div>
      )}
      {!isLoading && !isError && users && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">Name</th>
                <th className="py-3 pr-4">Email</th>
                <th className="py-3 pr-4">Role</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Last login</th>
                <th className="py-3 pr-4">Created</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <UserRow key={u.id} user={u} currentUserId={undefined} />
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <p className="py-6 text-center text-sm text-gray-500">No users found.</p>
          )}
        </div>
      )}
    </div>
  )
}
