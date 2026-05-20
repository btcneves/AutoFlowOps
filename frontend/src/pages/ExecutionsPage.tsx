import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { LiveIndicator } from '../components/ui/LiveIndicator'
import { useExecutions } from '../hooks/useExecutions'
import { useJobs } from '../hooks/useJobs'
import { useWebSocket } from '../hooks/useWebSocket'
import type { ExecutionRead } from '../types'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function StatusPill({ status }: { status: string }) {
  const { t } = useTranslation()
  const styles: Record<string, string> = {
    success: 'bg-green-100 text-green-700',
    failure: 'bg-red-100 text-red-700',
    timeout: 'bg-red-100 text-red-700',
    running: 'bg-blue-100 text-blue-700',
    queued: 'bg-gray-100 text-gray-700',
    retrying: 'bg-yellow-100 text-yellow-800',
  }
  const cls = styles[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {t(`statusLabel.${status}`, { defaultValue: status.charAt(0).toUpperCase() + status.slice(1) })}
    </span>
  )
}

function ExecutionRow({ exc, jobName }: { exc: ExecutionRead; jobName: string }) {
  const { t } = useTranslation()
  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pl-4 pr-4 text-xs text-gray-500">{formatDate(exc.started_at)}</td>
      <td className="py-3 pr-4">
        <Link to={`/jobs/${exc.job_id}`} className="text-sm text-blue-600 hover:underline">
          {jobName}
        </Link>
      </td>
      <td className="py-3 pr-4">
        <StatusPill status={exc.status} />
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">
        {exc.duration_ms !== null ? `${exc.duration_ms} ms` : '—'}
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">{exc.response_status_code ?? '—'}</td>
      <td className="py-3 pr-4 text-xs font-medium text-gray-500">{exc.trigger_type}</td>
      <td className="py-3 pr-4 text-xs text-red-600 max-w-[200px] truncate">{exc.error_message ?? '—'}</td>
      <td className="py-3 pr-4">
        <Link to={`/executions/${exc.id}`} className="text-xs text-blue-600 hover:underline">
          {t('executions.details')}
        </Link>
      </td>
    </tr>
  )
}

export function ExecutionsPage() {
  const { t } = useTranslation()
  const [statusFilter, setStatusFilter] = useState('')
  const [jobFilter, setJobFilter] = useState('')

  const queryClient = useQueryClient()
  const { lastEvent, status: wsStatus } = useWebSocket()

  useEffect(() => {
    if (
      lastEvent?.type === 'execution.started' ||
      lastEvent?.type === 'execution.completed'
    ) {
      void queryClient.invalidateQueries({ queryKey: ['executions'] })
    }
  }, [lastEvent, queryClient])

  const { data: jobs } = useJobs()
  const { data: executions, isLoading, isError } = useExecutions({
    status: statusFilter || undefined,
    job_id: jobFilter || undefined,
    limit: 100,
  })

  const jobMap = Object.fromEntries((jobs ?? []).map((j) => [j.id, j.name]))

  const statusOptions = [
    { label: t('executions.filterAll'), value: '' },
    { label: t('executions.filterSuccess'), value: 'success' },
    { label: t('executions.filterFailure'), value: 'failure' },
    { label: t('executions.filterTimeout'), value: 'timeout' },
    { label: t('executions.filterRunning'), value: 'running' },
    { label: t('executions.filterQueued'), value: 'queued' },
    { label: t('executions.filterRetrying'), value: 'retrying' },
  ]

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('executions.title')}</h1>
          <p className="mt-1 text-sm text-gray-500">{t('executions.subtitle')}</p>
        </div>
        <LiveIndicator status={wsStatus} />
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="flex gap-1">
          {statusOptions.map((opt) => (
            <button
              key={opt.value}
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

        <select
          value={jobFilter}
          onChange={(e) => setJobFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs shadow-sm focus:border-blue-500 focus:outline-none"
        >
          <option value="">{t('executions.allJobs')}</option>
          {(jobs ?? []).map((j) => (
            <option key={j.id} value={j.id}>{j.name}</option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-sm text-gray-500">{t('executions.loading')}</p>}

      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t('executions.error')}
        </div>
      )}

      {!isLoading && !isError && executions && executions.length === 0 && (
        <p className="text-sm text-gray-500">{t('executions.empty')}</p>
      )}

      {!isLoading && !isError && executions && executions.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pl-4 pr-4">{t('executions.colStarted')}</th>
                <th className="py-3 pr-4">{t('executions.colJob')}</th>
                <th className="py-3 pr-4">{t('executions.colStatus')}</th>
                <th className="py-3 pr-4">{t('executions.colDuration')}</th>
                <th className="py-3 pr-4">{t('executions.colHttp')}</th>
                <th className="py-3 pr-4">{t('executions.colTrigger')}</th>
                <th className="py-3 pr-4">{t('executions.colError')}</th>
                <th className="py-3 pr-4"></th>
              </tr>
            </thead>
            <tbody>
              {executions.map((exc) => (
                <ExecutionRow
                  key={exc.id}
                  exc={exc}
                  jobName={jobMap[exc.job_id] ?? exc.job_id.slice(0, 8)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
