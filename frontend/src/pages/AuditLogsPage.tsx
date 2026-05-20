import { useState } from 'react'
import type { AuditLogFilters } from '../api/audit_logs'
import { useAuditLogs } from '../hooks/useAuditLogs'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

const STATUS_COLOURS: Record<string, string> = {
  success: 'bg-green-100 text-green-700',
  failure: 'bg-red-100 text-red-700',
  denied: 'bg-yellow-100 text-yellow-700',
}

export function AuditLogsPage() {
  const [filters, setFilters] = useState<AuditLogFilters>({})
  const [draft, setDraft] = useState<AuditLogFilters>({})
  const { data: logs, isLoading, isError } = useAuditLogs(filters)

  function applyFilters() {
    const active: AuditLogFilters = {}
    if (draft.action) active.action = draft.action
    if (draft.resource_type) active.resource_type = draft.resource_type
    if (draft.status) active.status = draft.status
    if (draft.since) active.since = draft.since
    if (draft.until) active.until = draft.until
    setFilters(active)
  }

  function clearFilters() {
    setDraft({})
    setFilters({})
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
        <p className="mt-1 text-sm text-gray-500">
          Immutable record of security-relevant actions.
        </p>
      </div>

      <div className="mb-4 flex flex-wrap gap-2 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <input
          value={draft.action ?? ''}
          onChange={(e) => setDraft((d) => ({ ...d, action: e.target.value || undefined }))}
          placeholder="Filter by action…"
          className="rounded border border-gray-300 px-2 py-1.5 text-xs"
        />
        <input
          value={draft.resource_type ?? ''}
          onChange={(e) =>
            setDraft((d) => ({ ...d, resource_type: e.target.value || undefined }))
          }
          placeholder="Resource type…"
          className="rounded border border-gray-300 px-2 py-1.5 text-xs"
        />
        <select
          value={draft.status ?? ''}
          onChange={(e) => setDraft((d) => ({ ...d, status: e.target.value || undefined }))}
          className="rounded border border-gray-300 px-2 py-1.5 text-xs"
        >
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failure">Failure</option>
          <option value="denied">Denied</option>
        </select>
        <button
          onClick={applyFilters}
          className="rounded bg-gray-900 px-3 py-1.5 text-xs font-medium text-white"
        >
          Apply
        </button>
        <button
          onClick={clearFilters}
          className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
        >
          Clear
        </button>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading audit logs…</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not load audit logs.
        </div>
      )}
      {!isLoading && !isError && logs && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">Timestamp</th>
                <th className="py-3 pr-4">Action</th>
                <th className="py-3 pr-4">Resource</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log) => (
                <tr key={log.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="py-2.5 pr-4 pl-4 text-xs text-gray-500">
                    {formatDate(log.created_at)}
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs text-gray-800">{log.action}</td>
                  <td className="py-2.5 pr-4 text-xs text-gray-600">
                    {log.resource_type ? (
                      <span>
                        {log.resource_type}
                        {log.resource_id && (
                          <span className="ml-1 text-gray-400">
                            #{log.resource_id.slice(0, 8)}
                          </span>
                        )}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="py-2.5 pr-4">
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_COLOURS[log.status] ?? 'bg-gray-100 text-gray-600'}`}
                    >
                      {log.status}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-gray-500">
                    {log.ip_address ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length === 0 && (
            <p className="py-6 text-center text-sm text-gray-500">No audit log entries found.</p>
          )}
        </div>
      )}
    </div>
  )
}
