import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

const baseNavItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/jobs', label: 'Jobs' },
  { to: '/executions', label: 'Executions' },
  { to: '/webhooks', label: 'Webhooks' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/notifications', label: 'Channels' },
  { to: '/notification-templates', label: 'Templates' },
  { to: '/escalation-policies', label: 'Escalation' },
  { to: '/reports', label: 'Reports' },
]

const adminNavItems = [
  { to: '/users', label: 'Users' },
  { to: '/audit-logs', label: 'Audit Logs' },
]

export function Sidebar() {
  const { user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const navItems = isAdmin ? [...baseNavItems, ...adminNavItems] : baseNavItems

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-gray-200 bg-white px-4 py-6">
      <div className="mb-8">
        <span className="text-xl font-bold text-gray-900">AutoFlowOps</span>
      </div>
      <nav className="flex flex-col gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      {user && (
        <div className="mt-auto border-t border-gray-200 pt-4">
          <p className="truncate text-xs text-gray-500">{user.email}</p>
          <p className="mt-0.5 text-xs text-gray-400">{user.role}</p>
          <button
            onClick={handleLogout}
            className="mt-1 text-xs text-gray-400 hover:text-gray-600"
          >
            Sign out
          </button>
        </div>
      )}
    </aside>
  )
}
