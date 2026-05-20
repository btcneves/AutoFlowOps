import { useTranslation } from 'react-i18next'
import { useWebhooks } from '../hooks/useWebhooks'
import type { WebhookRead } from '../types'

const baseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

function receiveUrl(slug: string): string {
  return `${baseUrl}/api/webhooks/${slug}/receive`
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function StatusPill({ status }: { status: string }) {
  const { t } = useTranslation()
  const active = status === 'active'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
      }`}
    >
      {t(`statusLabel.${status}`, { defaultValue: active ? 'Active' : 'Paused' })}
    </span>
  )
}

function WebhookRow({ webhook }: { webhook: WebhookRead }) {
  const { t } = useTranslation()
  const url = receiveUrl(webhook.slug)

  function copyUrl() {
    void navigator.clipboard.writeText(url)
  }

  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">
        {webhook.name}
      </td>
      <td className="py-3 pr-4">
        <code className="rounded bg-gray-50 px-1.5 py-0.5 text-xs text-gray-700">
          {webhook.slug}
        </code>
      </td>
      <td className="py-3 pr-4">
        <StatusPill status={webhook.status} />
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(webhook.last_received_at)}</td>
      <td className="py-3 pr-4 text-right">
        <button
          onClick={copyUrl}
          className="rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50"
          title={url}
        >
          {t('webhooks.copyUrl')}
        </button>
      </td>
    </tr>
  )
}

export function WebhooksPage() {
  const { t } = useTranslation()
  const { data: webhooks, isLoading, isError } = useWebhooks()

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t('webhooks.title')}</h1>
        <p className="mt-1 text-sm text-gray-500">{t('webhooks.subtitle')}</p>
      </div>

      {isLoading && <p className="text-sm text-gray-500">{t('webhooks.loading')}</p>}

      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t('webhooks.error')}
        </div>
      )}

      {!isLoading && !isError && webhooks && webhooks.length === 0 && (
        <p className="text-sm text-gray-500">{t('webhooks.empty')}</p>
      )}

      {!isLoading && !isError && webhooks && webhooks.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">{t('webhooks.colName')}</th>
                <th className="py-3 pr-4">{t('webhooks.colSlug')}</th>
                <th className="py-3 pr-4">{t('webhooks.colStatus')}</th>
                <th className="py-3 pr-4">{t('webhooks.colLastReceived')}</th>
                <th className="py-3 pr-4 text-right">{t('webhooks.colActions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 pl-4">
              {webhooks.map((wh) => (
                <WebhookRow key={wh.id} webhook={wh} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
