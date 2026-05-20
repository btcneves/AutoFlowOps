import { createBrowserRouter } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { AlertsPage } from './pages/AlertsPage'
import { DashboardPage } from './pages/DashboardPage'
import { ReportsPage } from './pages/ReportsPage'
import { WebhooksPage } from './pages/WebhooksPage'

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <Layout />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: 'webhooks', element: <WebhooksPage /> },
        { path: 'alerts', element: <AlertsPage /> },
        { path: 'reports', element: <ReportsPage /> },
      ],
    },
  ],
  {
    future: {
      v7_relativeSplatPath: true,
    },
  }
)
