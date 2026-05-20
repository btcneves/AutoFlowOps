import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useExecution } from '../hooks/useExecutions'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function StatusPill({ status }: { status: string }) {
  const { t } = useTranslation()
  const styles: Record<string, string> = {
    success: 'bg-green-100 text-green-700',
    failure: 'bg-red-100 text-red-700',
    running: 'bg-blue-100 text-blue-700',
  }
  const cls = styles[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {t(`statusLabel.${status}`, { defaultValue: status.charAt(0).toUpperCase() + status.slice(1) })}
    </span>
  )
}

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-4 py-3 border-b border-gray-100 last:border-0">
      <dt className="w-40 shrink-0 text-xs font-medium text-gray-500">{label}</dt>
      <dd className="flex-1 text-sm text-gray-900 break-all">{children}</dd>
    </div>
  )
}

export function ExecutionDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const { data: exc, isLoading, isError } = useExecution(id!)

  if (isLoading) return <p className="text-sm text-gray-500">{t('executionDetail.loading')}</p>
  if (isError || !exc) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {t('executionDetail.notFound')}
      </div>
    )
  }

  return (
    <div className="max-w-3xl">
      <nav className="mb-3 text-xs text-gray-400">
        <Link to="/executions" className="hover:underline">{t('executionDetail.breadcrumb')}</Link>
        <span className="mx-1">/</span>
        <span>{exc.id.slice(0, 8)}…</span>
      </nav>

      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">{t('executionDetail.title')}</h1>
        <StatusPill status={exc.status} />
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <dl className="px-4">
          <InfoRow label={t('executionDetail.labelId')}>{exc.id}</InfoRow>
          <InfoRow label={t('executionDetail.labelJob')}>
            <Link to={`/jobs/${exc.job_id}`} className="text-blue-600 hover:underline">
              {exc.job_id}
            </Link>
          </InfoRow>
          <InfoRow label={t('executionDetail.labelStatus')}><StatusPill status={exc.status} /></InfoRow>
          <InfoRow label={t('executionDetail.labelTrigger')}>{exc.trigger_type}</InfoRow>
          <InfoRow label={t('executionDetail.labelStarted')}>{formatDate(exc.started_at)}</InfoRow>
          <InfoRow label={t('executionDetail.labelFinished')}>{formatDate(exc.finished_at)}</InfoRow>
          <InfoRow label={t('executionDetail.labelDuration')}>
            {exc.duration_ms !== null ? `${exc.duration_ms} ms` : '—'}
          </InfoRow>
          <InfoRow label={t('executionDetail.labelRetryAttempt')}>{exc.retry_attempt}</InfoRow>
        </dl>
      </div>

      <h2 className="mb-2 mt-6 text-lg font-semibold text-gray-900">{t('executionDetail.sectionRequest')}</h2>
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <dl className="px-4">
          <InfoRow label={t('executionDetail.labelMethod')}>{exc.request_method ?? '—'}</InfoRow>
          <InfoRow label={t('executionDetail.labelUrl')}>{exc.request_url ?? '—'}</InfoRow>
          <InfoRow label={t('executionDetail.labelHeadersMasked')}>
            {exc.request_headers_masked ? (
              <pre className="max-h-40 overflow-auto text-xs text-gray-700">
                {exc.request_headers_masked}
              </pre>
            ) : '—'}
          </InfoRow>
          <InfoRow label={t('executionDetail.labelBodyMasked')}>
            {exc.request_body_masked ? (
              <pre className="max-h-40 overflow-auto text-xs text-gray-700">
                {exc.request_body_masked}
              </pre>
            ) : '—'}
          </InfoRow>
        </dl>
      </div>

      <h2 className="mb-2 mt-6 text-lg font-semibold text-gray-900">{t('executionDetail.sectionResponse')}</h2>
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <dl className="px-4">
          <InfoRow label={t('executionDetail.labelHttpStatus')}>{exc.response_status_code ?? '—'}</InfoRow>
          <InfoRow label={t('executionDetail.labelBodyPreview')}>
            {exc.response_body_preview ? (
              <pre className="max-h-60 overflow-auto text-xs text-gray-700">
                {exc.response_body_preview}
              </pre>
            ) : '—'}
          </InfoRow>
          {exc.error_message && (
            <InfoRow label={t('executionDetail.labelError')}>
              <span className="text-red-600">{exc.error_message}</span>
            </InfoRow>
          )}
        </dl>
      </div>
    </div>
  )
}
