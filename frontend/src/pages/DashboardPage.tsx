import { useTranslation } from 'react-i18next'
import { ExecutionsChart } from '../components/ui/ExecutionsChart'
import { MetricCard } from '../components/ui/MetricCard'
import { StatusBadge } from '../components/ui/StatusBadge'
import { useHealth } from '../hooks/useHealth'
import { useStats } from '../hooks/useStats'

export function DashboardPage() {
  const { t } = useTranslation()
  const { data: health, isLoading: healthLoading, isError: healthError } = useHealth()
  const { data: stats, isLoading: statsLoading } = useStats()

  const backendStatus = healthLoading ? 'loading' : healthError ? 'error' : 'ok'

  const activeJobs = statsLoading ? '—' : (stats?.active_jobs ?? 0)
  const executions24h = statsLoading ? '—' : (stats?.executions_24h ?? 0)
  const failures24h = statsLoading ? '—' : (stats?.failures_24h ?? 0)
  const successRate = statsLoading
    ? '—'
    : stats && stats.executions_24h > 0
      ? `${stats.success_rate_24h}%`
      : 'N/A'

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('dashboard.title')}</h1>
          <p className="mt-1 text-sm text-gray-500">{t('dashboard.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          {t('dashboard.backend')} <StatusBadge status={backendStatus} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title={t('dashboard.activeJobs')}
          value={activeJobs}
          description={stats ? t('dashboard.totalJobs', { count: stats.total_jobs }) : t('dashboard.loadingStats')}
        />
        <MetricCard
          title={t('dashboard.executions24h')}
          value={executions24h}
          description={stats ? t('dashboard.allTimeExecutions', { count: stats.total_executions }) : t('dashboard.loadingStats')}
        />
        <MetricCard
          title={t('dashboard.failures24h')}
          value={failures24h}
          description={stats && stats.failures_24h === 0 ? t('dashboard.allClear') : t('dashboard.checkLogs')}
        />
        <MetricCard
          title={t('dashboard.successRate')}
          value={successRate}
          description={stats ? t('dashboard.last24h') : t('dashboard.loadingStats')}
        />
      </div>

      {stats && (
        <div className="mt-6">
          <ExecutionsChart data={stats.daily_stats} />
        </div>
      )}

      {!healthLoading && !healthError && health && (
        <p className="mt-6 text-xs text-gray-400">
          {t('dashboard.connectedTo', { app: health.app, env: health.env })}
        </p>
      )}

      {healthError && (
        <div className="mt-6 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t('dashboard.backendError')}
        </div>
      )}
    </div>
  )
}
