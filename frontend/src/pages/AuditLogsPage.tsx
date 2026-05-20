import { useState } from 'react'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
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
        <h1 className="text-2xl font-bold text-gray-900">{t('auditLogs.title')}</h1>
        <p className="mt-1 text-sm text-gray-500">{t('auditLogs.subtitle')}</p>
      </div>

      <div className="mb-4 flex flex-wrap gap-2 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
        <input
          value={draft.action ?? ''}
          onChange={(e) => setDraft((d) => ({ ...d, action: e.target.value || undefined }))}
          placeholder={t('auditLogs.filterAction')}
          className="rounded border border-gray-300 px-2 py-1.5 text-xs"
        />
        <input
          value={draft.resource_type ?? ''}
          onChange={(e) =>
            setDraft((d) => ({ ...d, resource_type: e.target.value || undefined }))
          }
          placeholder={t('auditLogs.filterResource')}
          className="rounded border border-gray-300 px-2 py-1.5 text-xs"
        />
        <select
          value={draft.status ?? ''}
          onChange={(e) => setDraft((d) => ({ ...d, status: e.target.value || undefined }))}
          className="rounded border border-gray-300 px-2 py-1.5 text-xs"
        >
          <option value="">{t('auditLogs.filterAllStatuses')}</option>
          <option value="success">{t('auditLogs.filterSuccess')}</option>
          <option value="failure">{t('auditLogs.filterFailure')}</option>
          <option value="denied">{t('auditLogs.filterDenied')}</option>
        </select>
        <button
          onClick={applyFilters}
          className="rounded bg-gray-900 px-3 py-1.5 text-xs font-medium text-white"
        >
          {t('auditLogs.apply')}
        </button>
        <button
          onClick={clearFilters}
          className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
        >
          {t('auditLogs.clear')}
        </button>
      </div>

      {isLoading && <p className="text-sm text-gray-500">{t('auditLogs.loading')}</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t('auditLogs.error')}
        </div>
      )}
      {!isLoading && !isError && logs && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">{t('auditLogs.colTimestamp')}</th>
                <th className="py-3 pr-4">{t('auditLogs.colAction')}</th>
                <th className="py-3 pr-4">{t('auditLogs.colResource')}</th>
                <th className="py-3 pr-4">{t('auditLogs.colStatus')}</th>
                <th className="py-3 pr-4">{t('auditLogs.colIp')}</th>
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
            <p className="py-6 text-center text-sm text-gray-500">{t('auditLogs.empty')}</p>
          )}
        </div>
      )}
    </div>
  )
}
