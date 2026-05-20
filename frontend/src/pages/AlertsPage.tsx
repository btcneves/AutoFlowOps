import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { LiveIndicator } from '../components/ui/LiveIndicator'
import { useAcknowledgeAlert, useAlerts, useResolveAlert } from '../hooks/useAlerts'
import { useWebSocket } from '../hooks/useWebSocket'
import type { AlertRead } from '../types'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function SeverityPill({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    error: 'bg-red-100 text-red-700',
    warning: 'bg-yellow-100 text-yellow-700',
    info: 'bg-blue-100 text-blue-700',
  }
  const cls = styles[severity] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {severity}
    </span>
  )
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    open: 'bg-red-50 text-red-600',
    acknowledged: 'bg-yellow-50 text-yellow-700',
    resolved: 'bg-green-50 text-green-700',
  }
  const cls = styles[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function AlertRow({ alert }: { alert: AlertRead }) {
  const resolve = useResolveAlert()
  const acknowledge = useAcknowledgeAlert()
  const isResolved = alert.status === 'resolved'

  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{alert.title}</td>
      <td className="py-3 pr-4 text-xs text-gray-500 max-w-xs truncate">{alert.message}</td>
      <td className="py-3 pr-4">
        <SeverityPill severity={alert.severity} />
      </td>
      <td className="py-3 pr-4">
        <StatusPill status={alert.status} />
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(alert.created_at)}</td>
      <td className="py-3 pr-4 text-right space-x-1">
        {!isResolved && alert.status === 'open' && (
          <button
            onClick={() => acknowledge.mutate(alert.id)}
            disabled={acknowledge.isPending}
            className="rounded px-2 py-1 text-xs text-yellow-600 hover:bg-yellow-50 disabled:opacity-50"
          >
            Acknowledge
          </button>
        )}
        {!isResolved && (
          <button
            onClick={() => resolve.mutate(alert.id)}
            disabled={resolve.isPending}
            className="rounded px-2 py-1 text-xs text-green-600 hover:bg-green-50 disabled:opacity-50"
          >
            Resolve
          </button>
        )}
      </td>
    </tr>
  )
}

export function AlertsPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const queryClient = useQueryClient()
  const { lastEvent, status: wsStatus } = useWebSocket()

  useEffect(() => {
    if (lastEvent?.type === 'alert.created') {
      void queryClient.invalidateQueries({ queryKey: ['alerts'] })
    }
  }, [lastEvent, queryClient])

  const { data: alerts, isLoading, isError } = useAlerts(statusFilter)

  const filterOptions: { label: string; value: string | undefined }[] = [
    { label: 'All', value: undefined },
    { label: 'Open', value: 'open' },
    { label: 'Acknowledged', value: 'acknowledged' },
    { label: 'Resolved', value: 'resolved' },
  ]

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="mt-1 text-sm text-gray-500">
            Automatic alerts generated on job failures and other events.
          </p>
        </div>
        <div className="flex items-center gap-4">
        <LiveIndicator status={wsStatus} />
        <div className="flex gap-1">
          {filterOptions.map((opt) => (
            <button
              key={opt.label}
              onClick={() => setStatusFilter(opt.value)}
              className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                statusFilter === opt.value
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        </div>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading alerts…</p>}

      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not load alerts. Make sure the API is running.
        </div>
      )}

      {!isLoading && !isError && alerts && alerts.length === 0 && (
        <p className="text-sm text-gray-500">No alerts found.</p>
      )}

      {!isLoading && !isError && alerts && alerts.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">Title</th>
                <th className="py-3 pr-4">Message</th>
                <th className="py-3 pr-4">Severity</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Created</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {alerts.map((alert) => (
                <AlertRow key={alert.id} alert={alert} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
