import { FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useCreateNotificationTemplate,
  useDeleteNotificationTemplate,
  useNotificationTemplates,
  useUpdateNotificationTemplate,
} from '../hooks/useNotificationTemplates'
import type { NotificationTemplateRead } from '../types'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

function TemplateForm({
  editing,
  onDone,
}: {
  editing: NotificationTemplateRead | null
  onDone: () => void
}) {
  const { t } = useTranslation()
  const create = useCreateNotificationTemplate()
  const update = useUpdateNotificationTemplate()
  const [name, setName] = useState(editing?.name ?? '')
  const [severityFilter, setSeverityFilter] = useState(editing?.severity_filter ?? '')
  const [titleTemplate, setTitleTemplate] = useState(editing?.title_template ?? '{title}')
  const [bodyTemplate, setBodyTemplate] = useState(
    editing?.body_template ?? '{title}\n\nSeverity: {severity}\n{message}'
  )
  const [isDefault, setIsDefault] = useState(editing?.is_default ?? false)
  const [error, setError] = useState<string | null>(null)

  const isPending = create.isPending || update.isPending

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (!name.trim()) {
      setError(t('templates.errorName'))
      return
    }
    const payload = {
      name: name.trim(),
      severity_filter: severityFilter || null,
      title_template: titleTemplate,
      body_template: bodyTemplate,
      is_default: isDefault,
    }
    const mutation = editing
      ? update.mutateAsync({ id: editing.id, payload })
      : create.mutateAsync(payload)
    void mutation.then(onDone).catch((err: Error) => setError(err.message))
  }

  const severityOptions = [
    { value: '', label: t('templates.severityAll') },
    { value: 'error', label: t('templates.severityError') },
    { value: 'warning', label: t('templates.severityWarning') },
    { value: 'info', label: t('templates.severityInfo') },
  ]

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">
          {editing ? t('templates.formTitleEdit') : t('templates.formTitleNew')}
        </h2>
        {editing && (
          <button
            type="button"
            onClick={onDone}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {t('templates.cancel')}
          </button>
        )}
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <label className="text-xs font-medium text-gray-600">
          {t('templates.labelName')}
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs font-medium text-gray-600">
          {t('templates.labelSeverityFilter')}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          >
            {severityOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 pt-6 text-xs font-medium text-gray-600">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
          />
          {t('templates.labelDefault')}
        </label>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label className="text-xs font-medium text-gray-600">
          {t('templates.labelTitleTemplate')}
          <input
            value={titleTemplate}
            onChange={(e) => setTitleTemplate(e.target.value)}
            placeholder="{title}"
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono"
          />
        </label>
        <label className="text-xs font-medium text-gray-600">
          {t('templates.labelBodyTemplate')}
          <textarea
            value={bodyTemplate}
            onChange={(e) => setBodyTemplate(e.target.value)}
            rows={3}
            placeholder="{title}\n\nSeverity: {severity}\n{message}"
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono"
          />
        </label>
      </div>
      <p className="mt-2 text-xs text-gray-400">{t('templates.availableVars')}</p>
      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
      <button
        disabled={isPending}
        className="mt-4 rounded bg-gray-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
      >
        {editing ? t('templates.saveTemplate') : t('templates.createTemplate')}
      </button>
    </form>
  )
}

function TemplateRow({
  template,
  onEdit,
}: {
  template: NotificationTemplateRead
  onEdit: (t: NotificationTemplateRead) => void
}) {
  const { t } = useTranslation()
  const remove = useDeleteNotificationTemplate()
  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{template.name}</td>
      <td className="py-3 pr-4 text-xs text-gray-600">
        {template.severity_filter ?? 'all'}
      </td>
      <td className="py-3 pr-4 text-xs font-mono text-gray-600">{template.title_template}</td>
      <td className="py-3 pr-4 text-xs text-gray-500">
        {template.is_default ? t('templates.yes') : '—'}
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(template.created_at)}</td>
      <td className="py-3 pr-4 text-right space-x-1">
        <button
          onClick={() => onEdit(template)}
          className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          {t('templates.edit')}
        </button>
        <button
          onClick={() => remove.mutate(template.id)}
          disabled={remove.isPending}
          className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
        >
          {t('templates.delete')}
        </button>
      </td>
    </tr>
  )
}

export function NotificationTemplatesPage() {
  const { t } = useTranslation()
  const { data: templates, isLoading, isError } = useNotificationTemplates()
  const [editing, setEditing] = useState<NotificationTemplateRead | null>(null)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('templates.title')}</h1>
        <p className="mt-1 text-sm text-gray-500">{t('templates.subtitle')}</p>
      </div>

      <TemplateForm editing={editing} onDone={() => setEditing(null)} />

      {isLoading && <p className="text-sm text-gray-500">{t('templates.loading')}</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t('templates.error')}
        </div>
      )}
      {!isLoading && !isError && templates && templates.length === 0 && (
        <p className="text-sm text-gray-500">{t('templates.empty')}</p>
      )}
      {!isLoading && !isError && templates && templates.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">{t('templates.colName')}</th>
                <th className="py-3 pr-4">{t('templates.colSeverity')}</th>
                <th className="py-3 pr-4">{t('templates.colTitleTemplate')}</th>
                <th className="py-3 pr-4">{t('templates.colDefault')}</th>
                <th className="py-3 pr-4">{t('templates.colCreated')}</th>
                <th className="py-3 pr-4 text-right">{t('templates.colActions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {templates.map((tmpl) => (
                <TemplateRow key={tmpl.id} template={tmpl} onEdit={setEditing} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
