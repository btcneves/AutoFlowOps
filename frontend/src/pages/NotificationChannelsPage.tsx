import { FormEvent, useMemo, useState } from 'react'
import {
  useActivateNotificationChannel,
  useCreateNotificationChannel,
  useDeactivateNotificationChannel,
  useDeleteNotificationChannel,
  useNotificationChannels,
  useNotificationDeliveries,
  useTestNotificationChannel,
  useUpdateNotificationChannel,
} from '../hooks/useNotifications'
import type {
  NotificationChannelRead,
  NotificationChannelStatus,
  NotificationChannelType,
  NotificationChannelUpdatePayload,
} from '../types'

const typeLabels: Record<NotificationChannelType, string> = {
  discord_webhook: 'Discord webhook',
  slack_webhook: 'Slack webhook',
  telegram_message: 'Telegram',
  smtp_email: 'SMTP email',
  custom_webhook: 'Custom webhook',
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function StatusPill({ status }: { status: string }) {
  const active = status === 'active'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
      }`}
    >
      {active ? 'Active' : 'Paused'}
    </span>
  )
}

function ChannelForm({
  editing,
  onDone,
}: {
  editing: NotificationChannelRead | null
  onDone: () => void
}) {
  const create = useCreateNotificationChannel()
  const update = useUpdateNotificationChannel()
  const [name, setName] = useState(editing?.name ?? '')
  const [type, setType] = useState<NotificationChannelType>(
    editing?.type ?? 'discord_webhook'
  )
  const [status, setStatus] = useState<NotificationChannelStatus>(
    editing?.status ?? 'active'
  )
  const [webhookUrl, setWebhookUrl] = useState('')
  const [slackUrl, setSlackUrl] = useState('')
  const [telegramToken, setTelegramToken] = useState('')
  const [telegramChatId, setTelegramChatId] = useState('')
  const [customUrl, setCustomUrl] = useState('')
  const [customHeaders, setCustomHeaders] = useState('')
  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState('587')
  const [smtpUsername, setSmtpUsername] = useState('')
  const [smtpPassword, setSmtpPassword] = useState('')
  const [smtpFrom, setSmtpFrom] = useState('')
  const [smtpTo, setSmtpTo] = useState('')
  const [smtpTls, setSmtpTls] = useState(true)
  const [smtpSsl, setSmtpSsl] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isPending = create.isPending || update.isPending

  const maskedConfig = useMemo(() => {
    if (!editing) return null
    return Object.entries(editing.config_masked)
      .map(([key, value]) => `${key}: ${String(value ?? '—')}`)
      .join(' · ')
  }, [editing])

  function buildConfig(): Record<string, unknown> | null {
    if (type === 'discord_webhook') {
      if (!webhookUrl) return null
      return { webhook_url: webhookUrl }
    }
    if (type === 'slack_webhook') {
      if (!slackUrl) return null
      return { webhook_url: slackUrl }
    }
    if (type === 'telegram_message') {
      if (!telegramToken || !telegramChatId) return null
      return { bot_token: telegramToken, chat_id: telegramChatId }
    }
    if (type === 'custom_webhook') {
      if (!customUrl) return null
      let headers: Record<string, string> = {}
      if (customHeaders.trim()) {
        headers = JSON.parse(customHeaders) as Record<string, string>
      }
      return { url: customUrl, method: 'POST', headers }
    }
    if (!smtpHost || !smtpPort || !smtpFrom || !smtpTo) return null
    return {
      host: smtpHost,
      port: Number(smtpPort),
      username: smtpUsername || null,
      password: smtpPassword || null,
      from_email: smtpFrom,
      to_email: smtpTo,
      use_tls: smtpTls,
      use_ssl: smtpSsl,
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const config = buildConfig()
      if (!name.trim()) {
        setError('Name is required.')
        return
      }
      if (!editing && config === null) {
        setError('Channel configuration is required.')
        return
      }
      const payload: NotificationChannelUpdatePayload = {
        name: name.trim(),
        type,
        status,
      }
      if (config !== null) payload.config = config
      const mutation = editing
        ? update.mutateAsync({ id: editing.id, payload })
        : create.mutateAsync({ name: name.trim(), type, status, config: config ?? {} })
      void mutation.then(onDone).catch((err: Error) => setError(err.message))
    } catch {
      setError('Headers must be valid JSON.')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">
          {editing ? 'Edit channel' : 'New channel'}
        </h2>
        {editing && (
          <button type="button" onClick={onDone} className="text-xs text-gray-500 hover:text-gray-700">
            Cancel
          </button>
        )}
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <label className="text-xs font-medium text-gray-600">
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
        </label>
        <label className="text-xs font-medium text-gray-600">
          Type
          <select value={type} onChange={(e) => setType(e.target.value as NotificationChannelType)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm">
            <option value="discord_webhook">Discord webhook</option>
            <option value="slack_webhook">Slack webhook</option>
            <option value="telegram_message">Telegram</option>
            <option value="smtp_email">SMTP email</option>
            <option value="custom_webhook">Custom webhook</option>
          </select>
        </label>
        <label className="text-xs font-medium text-gray-600">
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value as NotificationChannelStatus)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm">
            <option value="active">Active</option>
            <option value="paused">Paused</option>
          </select>
        </label>
      </div>

      {editing && maskedConfig && (
        <p className="mt-3 text-xs text-gray-500">Saved config: {maskedConfig}</p>
      )}

      {type === 'discord_webhook' && (
        <div className="mt-3">
          <label className="text-xs font-medium text-gray-600">
            Webhook URL
            <input value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} placeholder={editing ? 'Leave blank to keep current URL' : ''} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
        </div>
      )}

      {type === 'slack_webhook' && (
        <div className="mt-3">
          <label className="text-xs font-medium text-gray-600">
            Slack Incoming Webhook URL
            <input
              value={slackUrl}
              onChange={(e) => setSlackUrl(e.target.value)}
              placeholder={editing ? 'Leave blank to keep current URL' : 'https://hooks.slack.com/services/…'}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
        </div>
      )}

      {type === 'telegram_message' && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="text-xs font-medium text-gray-600">
            Bot Token
            <input
              type="password"
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
              placeholder={editing ? 'Leave blank to keep current token' : '123456:ABC…'}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs font-medium text-gray-600">
            Chat ID
            <input
              value={telegramChatId}
              onChange={(e) => setTelegramChatId(e.target.value)}
              placeholder="-100123456789"
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
        </div>
      )}

      {type === 'custom_webhook' && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="text-xs font-medium text-gray-600">
            URL
            <input value={customUrl} onChange={(e) => setCustomUrl(e.target.value)} placeholder={editing ? 'Leave blank to keep current URL' : ''} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            Headers JSON
            <input value={customHeaders} onChange={(e) => setCustomHeaders(e.target.value)} placeholder='{"X-Event":"autoflowops"}' className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
        </div>
      )}

      {type === 'smtp_email' && (
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          <label className="text-xs font-medium text-gray-600">
            Host
            <input value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            Port
            <input value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            Username
            <input value={smtpUsername} onChange={(e) => setSmtpUsername(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            Password
            <input type="password" value={smtpPassword} onChange={(e) => setSmtpPassword(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            From
            <input value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            To
            <input value={smtpTo} onChange={(e) => setSmtpTo(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="flex items-center gap-2 pt-6 text-xs font-medium text-gray-600">
            <input type="checkbox" checked={smtpTls} onChange={(e) => setSmtpTls(e.target.checked)} />
            TLS
          </label>
          <label className="flex items-center gap-2 pt-6 text-xs font-medium text-gray-600">
            <input type="checkbox" checked={smtpSsl} onChange={(e) => setSmtpSsl(e.target.checked)} />
            SSL
          </label>
        </div>
      )}

      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
      <button disabled={isPending} className="mt-4 rounded bg-gray-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
        {editing ? 'Save channel' : 'Create channel'}
      </button>
    </form>
  )
}

function ChannelRow({
  channel,
  onEdit,
}: {
  channel: NotificationChannelRead
  onEdit: (channel: NotificationChannelRead) => void
}) {
  const activate = useActivateNotificationChannel()
  const deactivate = useDeactivateNotificationChannel()
  const remove = useDeleteNotificationChannel()
  const test = useTestNotificationChannel()
  const isActive = channel.status === 'active'

  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{channel.name}</td>
      <td className="py-3 pr-4 text-xs text-gray-600">{typeLabels[channel.type]}</td>
      <td className="py-3 pr-4"><StatusPill status={channel.status} /></td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(channel.last_tested_at)}</td>
      <td className="py-3 pr-4 text-right space-x-1">
        <button onClick={() => test.mutate(channel.id)} disabled={test.isPending} className="rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 disabled:opacity-50">Test</button>
        <button onClick={() => onEdit(channel)} className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">Edit</button>
        {isActive ? (
          <button onClick={() => deactivate.mutate(channel.id)} className="rounded px-2 py-1 text-xs text-yellow-600 hover:bg-yellow-50">Pause</button>
        ) : (
          <button onClick={() => activate.mutate(channel.id)} className="rounded px-2 py-1 text-xs text-green-600 hover:bg-green-50">Activate</button>
        )}
        <button onClick={() => remove.mutate(channel.id)} className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50">Delete</button>
      </td>
    </tr>
  )
}

export function NotificationChannelsPage() {
  const { data: channels, isLoading, isError } = useNotificationChannels()
  const { data: deliveries } = useNotificationDeliveries()
  const [editing, setEditing] = useState<NotificationChannelRead | null>(null)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Notification Channels</h1>
        <p className="mt-1 text-sm text-gray-500">
          External destinations for critical operational alerts.
        </p>
      </div>

      <ChannelForm editing={editing} onDone={() => setEditing(null)} />

      {isLoading && <p className="text-sm text-gray-500">Loading channels…</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not load notification channels. Make sure the API is running.
        </div>
      )}
      {!isLoading && !isError && channels && channels.length === 0 && (
        <p className="text-sm text-gray-500">No notification channels configured yet.</p>
      )}
      {!isLoading && !isError && channels && channels.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">Name</th>
                <th className="py-3 pr-4">Type</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Last Test</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {channels.map((channel) => (
                <ChannelRow key={channel.id} channel={channel} onEdit={setEditing} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {deliveries && deliveries.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">Recent deliveries</h2>
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="py-3 pr-4 pl-4">Channel</th>
                  <th className="py-3 pr-4">Status</th>
                  <th className="py-3 pr-4">Error</th>
                  <th className="py-3 pr-4">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {deliveries.slice(0, 10).map((delivery) => (
                  <tr key={delivery.id} className="border-t border-gray-100">
                    <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{delivery.channel_name}</td>
                    <td className="py-3 pr-4 text-xs text-gray-600">{delivery.status}</td>
                    <td className="py-3 pr-4 text-xs text-gray-500">{delivery.error_message ?? '—'}</td>
                    <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(delivery.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
