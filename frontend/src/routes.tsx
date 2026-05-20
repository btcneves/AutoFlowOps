import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AdminRoute } from './components/layout/AdminRoute'
import { Layout } from './components/layout/Layout'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { AlertsPage } from './pages/AlertsPage'
import { AuditLogsPage } from './pages/AuditLogsPage'
import { DashboardPage } from './pages/DashboardPage'
import { EscalationPoliciesPage } from './pages/EscalationPoliciesPage'
import { ExecutionDetailPage } from './pages/ExecutionDetailPage'
import { ExecutionsPage } from './pages/ExecutionsPage'
import { JobDetailPage } from './pages/JobDetailPage'
import { JobFormPage } from './pages/JobFormPage'
import { JobsPage } from './pages/JobsPage'
import { LoginPage } from './pages/LoginPage'
import { NotificationChannelsPage } from './pages/NotificationChannelsPage'
import { NotificationTemplatesPage } from './pages/NotificationTemplatesPage'
import { ReportsPage } from './pages/ReportsPage'
import { UsersPage } from './pages/UsersPage'
import { WebhooksPage } from './pages/WebhooksPage'

export const router = createBrowserRouter(
  [
    {
      path: '/login',
      element: <LoginPage />,
    },
    {
      path: '/',
      element: (
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      ),
      children: [
        { index: true, element: <DashboardPage /> },
        { path: 'jobs', element: <JobsPage /> },
        { path: 'jobs/new', element: <JobFormPage /> },
        { path: 'jobs/:id', element: <JobDetailPage /> },
        { path: 'jobs/:id/edit', element: <JobFormPage /> },
        { path: 'executions', element: <ExecutionsPage /> },
        { path: 'executions/:id', element: <ExecutionDetailPage /> },
        { path: 'webhooks', element: <WebhooksPage /> },
        { path: 'alerts', element: <AlertsPage /> },
        { path: 'notifications', element: <NotificationChannelsPage /> },
        { path: 'notification-templates', element: <NotificationTemplatesPage /> },
        { path: 'escalation-policies', element: <EscalationPoliciesPage /> },
        { path: 'reports', element: <ReportsPage /> },
        {
          path: 'users',
          element: (
            <AdminRoute>
              <UsersPage />
            </AdminRoute>
          ),
        },
        {
          path: 'audit-logs',
          element: (
            <AdminRoute>
              <AuditLogsPage />
            </AdminRoute>
          ),
        },
      ],
    },
    { path: '*', element: <Navigate to="/" replace /> },
  ],
  {
    future: {
      v7_relativeSplatPath: true,
    },
  }
)
