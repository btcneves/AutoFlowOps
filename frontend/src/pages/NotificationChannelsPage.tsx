import { FormEvent, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
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
      {active ? t('channels.statusActive') : t('channels.statusPaused')}
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
  const { t } = useTranslation()
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
  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState('587')
  const [smtpUsername, setSmtpUsername] = useState('')
  const [smtpPassword, setSmtpPassword] = useState('')
  const [smtpFrom, setSmtpFrom] = useState('')
  const [smtpTo, setSmtpTo] = useState('')
  const [smtpTls, setSmtpTls] = useState(true)
  const [smtpSsl, setSmtpSsl] = useState(false)
  const [pdRoutingKey, setPdRoutingKey] = useState('')
  const [pdDedupKeyTemplate, setPdDedupKeyTemplate] = useState('')
  const [opsApiKey, setOpsApiKey] = useState('')
  const [opsRegion, setOpsRegion] = useState<'us' | 'eu'>('us')
  const [opsResponders, setOpsResponders] = useState('')
  const [opsPriority, setOpsPriority] = useState('')
  const [customUrl, setCustomUrl] = useState('')
  const [customHeaders, setCustomHeaders] = useState('')
  const [customPayloadTemplate, setCustomPayloadTemplate] = useState('')
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
      const cwResult: Record<string, unknown> = { url: customUrl, method: 'POST', headers }
      if (customPayloadTemplate.trim()) cwResult.payload_template = customPayloadTemplate.trim()
      return cwResult
    }
    if (type === 'pagerduty') {
      if (!pdRoutingKey) return null
      const pdResult: Record<string, unknown> = { routing_key: pdRoutingKey }
      if (pdDedupKeyTemplate.trim()) pdResult.dedup_key_template = pdDedupKeyTemplate.trim()
      return pdResult
    }
    if (type === 'opsgenie') {
      if (!opsApiKey) return null
      const result: Record<string, unknown> = { api_key: opsApiKey, region: opsRegion }
      if (opsResponders.trim()) {
        result.responders = JSON.parse(opsResponders) as unknown[]
      }
      if (opsPriority) result.priority = opsPriority
      return result
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
        setError(t('channels.errorName'))
        return
      }
      if (!editing && config === null) {
        setError(t('channels.errorConfig'))
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
      setError(t('channels.errorHeaders'))
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">
          {editing ? t('channels.formTitleEdit') : t('channels.formTitleNew')}
        </h2>
        {editing && (
          <button type="button" onClick={onDone} className="text-xs text-gray-500 hover:text-gray-700">
            {t('channels.cancel')}
          </button>
        )}
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <label className="text-xs font-medium text-gray-600">
          {t('channels.labelName')}
          <input value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
        </label>
        <label className="text-xs font-medium text-gray-600">
          {t('channels.labelType')}
          <select value={type} onChange={(e) => setType(e.target.value as NotificationChannelType)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm">
            <option value="discord_webhook">{t('channels.typeDiscord')}</option>
            <option value="slack_webhook">{t('channels.typeSlack')}</option>
            <option value="telegram_message">{t('channels.typeTelegram')}</option>
            <option value="smtp_email">{t('channels.typeSmtp')}</option>
            <option value="custom_webhook">{t('channels.typeCustom')}</option>
            <option value="pagerduty">{t('channels.typePagerDuty')}</option>
            <option value="opsgenie">{t('channels.typeOpsGenie')}</option>
          </select>
        </label>
        <label className="text-xs font-medium text-gray-600">
          {t('channels.labelStatus')}
          <select value={status} onChange={(e) => setStatus(e.target.value as NotificationChannelStatus)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm">
            <option value="active">{t('channels.statusActive')}</option>
            <option value="paused">{t('channels.statusPaused')}</option>
          </select>
        </label>
      </div>

      {editing && maskedConfig && (
        <p className="mt-3 text-xs text-gray-500">{t('channels.savedConfig', { config: maskedConfig })}</p>
      )}

      {type === 'discord_webhook' && (
        <div className="mt-3">
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelWebhookUrl')}
            <input value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} placeholder={editing ? t('channels.placeholderKeepUrl') : ''} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
        </div>
      )}

      {type === 'slack_webhook' && (
        <div className="mt-3">
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelSlackUrl')}
            <input
              value={slackUrl}
              onChange={(e) => setSlackUrl(e.target.value)}
              placeholder={editing ? t('channels.placeholderKeepUrl') : t('channels.placeholderSlackUrl')}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
        </div>
      )}

      {type === 'telegram_message' && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelBotToken')}
            <input
              type="password"
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
              placeholder={editing ? t('channels.placeholderKeepToken') : t('channels.placeholderBotToken')}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelChatId')}
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
            {t('channels.labelUrl')}
            <input value={customUrl} onChange={(e) => setCustomUrl(e.target.value)} placeholder={editing ? t('channels.placeholderKeepUrl') : ''} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelHeadersJson')}
            <input value={customHeaders} onChange={(e) => setCustomHeaders(e.target.value)} placeholder={t('channels.placeholderHeaders')} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="col-span-2 text-xs font-medium text-gray-600">
            {t('channels.labelPayloadTemplate')}
            <input value={customPayloadTemplate} onChange={(e) => setCustomPayloadTemplate(e.target.value)} placeholder={t('channels.placeholderPayloadTemplate')} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono" />
          </label>
        </div>
      )}

      {type === 'smtp_email' && (
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelHost')}
            <input value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelPort')}
            <input value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelUsername')}
            <input value={smtpUsername} onChange={(e) => setSmtpUsername(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelPassword')}
            <input type="password" value={smtpPassword} onChange={(e) => setSmtpPassword(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelFrom')}
            <input value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelTo')}
            <input value={smtpTo} onChange={(e) => setSmtpTo(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </label>
          <label className="flex items-center gap-2 pt-6 text-xs font-medium text-gray-600">
            <input type="checkbox" checked={smtpTls} onChange={(e) => setSmtpTls(e.target.checked)} />
            {t('channels.labelTls')}
          </label>
          <label className="flex items-center gap-2 pt-6 text-xs font-medium text-gray-600">
            <input type="checkbox" checked={smtpSsl} onChange={(e) => setSmtpSsl(e.target.checked)} />
            {t('channels.labelSsl')}
          </label>
        </div>
      )}

      {type === 'pagerduty' && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelRoutingKey')}
            <input
              type="password"
              value={pdRoutingKey}
              onChange={(e) => setPdRoutingKey(e.target.value)}
              placeholder={editing ? t('channels.placeholderKeepRoutingKey') : t('channels.placeholderRoutingKey')}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelDedupKeyTemplate')}
            <input
              value={pdDedupKeyTemplate}
              onChange={(e) => setPdDedupKeyTemplate(e.target.value)}
              placeholder={t('channels.placeholderDedupKeyTemplate')}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
        </div>
      )}

      {type === 'opsgenie' && (
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelApiKey')}
            <input
              type="password"
              value={opsApiKey}
              onChange={(e) => setOpsApiKey(e.target.value)}
              placeholder={editing ? t('channels.placeholderKeepApiKey') : t('channels.placeholderApiKey')}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelOpsGenieRegion')}
            <select value={opsRegion} onChange={(e) => setOpsRegion(e.target.value as 'us' | 'eu')} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm">
              <option value="us">US</option>
              <option value="eu">EU</option>
            </select>
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelPriority')}
            <select value={opsPriority} onChange={(e) => setOpsPriority(e.target.value)} className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm">
              <option value="">{t('channels.priorityAuto')}</option>
              <option value="P1">P1</option>
              <option value="P2">P2</option>
              <option value="P3">P3</option>
              <option value="P4">P4</option>
              <option value="P5">P5</option>
            </select>
          </label>
          <label className="text-xs font-medium text-gray-600">
            {t('channels.labelResponders')}
            <input
              value={opsResponders}
              onChange={(e) => setOpsResponders(e.target.value)}
              placeholder={t('channels.placeholderResponders')}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
        </div>
      )}

      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
      <button disabled={isPending} className="mt-4 rounded bg-gray-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
        {editing ? t('channels.saveChannel') : t('channels.createChannel')}
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
  const { t } = useTranslation()
  const activate = useActivateNotificationChannel()
  const deactivate = useDeactivateNotificationChannel()
  const remove = useDeleteNotificationChannel()
  const test = useTestNotificationChannel()
  const isActive = channel.status === 'active'

  const typeLabels: Record<NotificationChannelType, string> = {
    discord_webhook: t('channels.typeDiscord'),
    slack_webhook: t('channels.typeSlack'),
    telegram_message: t('channels.typeTelegram'),
    smtp_email: t('channels.typeSmtp'),
    custom_webhook: t('channels.typeCustom'),
    pagerduty: t('channels.typePagerDuty'),
    opsgenie: t('channels.typeOpsGenie'),
  }

  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{channel.name}</td>
      <td className="py-3 pr-4 text-xs text-gray-600">{typeLabels[channel.type]}</td>
      <td className="py-3 pr-4"><StatusPill status={channel.status} /></td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(channel.last_tested_at)}</td>
      <td className="py-3 pr-4 text-right space-x-1">
        <button onClick={() => test.mutate(channel.id)} disabled={test.isPending} className="rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 disabled:opacity-50">{t('channels.test')}</button>
        <button onClick={() => onEdit(channel)} className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">{t('channels.edit')}</button>
        {isActive ? (
          <button onClick={() => deactivate.mutate(channel.id)} className="rounded px-2 py-1 text-xs text-yellow-600 hover:bg-yellow-50">{t('channels.pause')}</button>
        ) : (
          <button onClick={() => activate.mutate(channel.id)} className="rounded px-2 py-1 text-xs text-green-600 hover:bg-green-50">{t('channels.activate')}</button>
        )}
        <button onClick={() => remove.mutate(channel.id)} className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50">{t('channels.delete')}</button>
      </td>
    </tr>
  )
}

export function NotificationChannelsPage() {
  const { t } = useTranslation()
  const { data: channels, isLoading, isError } = useNotificationChannels()
  const { data: deliveries } = useNotificationDeliveries()
  const [editing, setEditing] = useState<NotificationChannelRead | null>(null)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('channels.title')}</h1>
        <p className="mt-1 text-sm text-gray-500">{t('channels.subtitle')}</p>
      </div>

      <ChannelForm editing={editing} onDone={() => setEditing(null)} />

      {isLoading && <p className="text-sm text-gray-500">{t('channels.loading')}</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t('channels.error')}
        </div>
      )}
      {!isLoading && !isError && channels && channels.length === 0 && (
        <p className="text-sm text-gray-500">{t('channels.empty')}</p>
      )}
      {!isLoading && !isError && channels && channels.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">{t('channels.colName')}</th>
                <th className="py-3 pr-4">{t('channels.colType')}</th>
                <th className="py-3 pr-4">{t('channels.colStatus')}</th>
                <th className="py-3 pr-4">{t('channels.colLastTest')}</th>
                <th className="py-3 pr-4 text-right">{t('channels.colActions')}</th>
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
          <h2 className="mb-3 text-sm font-semibold text-gray-900">{t('channels.deliveriesTitle')}</h2>
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="py-3 pr-4 pl-4">{t('channels.colChannel')}</th>
                  <th className="py-3 pr-4">{t('channels.colStatus')}</th>
                  <th className="py-3 pr-4">{t('channels.colError')}</th>
                  <th className="py-3 pr-4">{t('channels.colCreated')}</th>
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
