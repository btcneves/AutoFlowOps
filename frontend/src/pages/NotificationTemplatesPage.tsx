import { FormEvent, useState } from 'react'
import {
  useCreateNotificationTemplate,
  useDeleteNotificationTemplate,
  useNotificationTemplates,
  useUpdateNotificationTemplate,
} from '../hooks/useNotificationTemplates'
import type { NotificationTemplateRead } from '../types'

const SEVERITY_OPTIONS = [
  { value: '', label: 'All severities (catch-all)' },
  { value: 'error', label: 'Error' },
  { value: 'warning', label: 'Warning' },
  { value: 'info', label: 'Info' },
]

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
      setError('Name is required.')
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

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">
          {editing ? 'Edit template' : 'New template'}
        </h2>
        {editing && (
          <button
            type="button"
            onClick={onDone}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        )}
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <label className="text-xs font-medium text-gray-600">
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs font-medium text-gray-600">
          Severity filter
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          >
            {SEVERITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 pt-6 text-xs font-medium text-gray-600">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
          />
          Default template
        </label>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label className="text-xs font-medium text-gray-600">
          Title template
          <input
            value={titleTemplate}
            onChange={(e) => setTitleTemplate(e.target.value)}
            placeholder="{title}"
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono"
          />
        </label>
        <label className="text-xs font-medium text-gray-600">
          Body template
          <textarea
            value={bodyTemplate}
            onChange={(e) => setBodyTemplate(e.target.value)}
            rows={3}
            placeholder="{title}\n\nSeverity: {severity}\n{message}"
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono"
          />
        </label>
      </div>
      <p className="mt-2 text-xs text-gray-400">
        Available variables: {'{title}'}, {'{severity}'}, {'{message}'}, {'{alert_id}'}
      </p>
      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
      <button
        disabled={isPending}
        className="mt-4 rounded bg-gray-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
      >
        {editing ? 'Save template' : 'Create template'}
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
  const remove = useDeleteNotificationTemplate()
  return (
    <tr className="border-t border-gray-100">
      <td className="py-3 pr-4 pl-4 text-sm font-medium text-gray-900">{template.name}</td>
      <td className="py-3 pr-4 text-xs text-gray-600">
        {template.severity_filter ?? 'all'}
      </td>
      <td className="py-3 pr-4 text-xs font-mono text-gray-600">{template.title_template}</td>
      <td className="py-3 pr-4 text-xs text-gray-500">
        {template.is_default ? 'Yes' : '—'}
      </td>
      <td className="py-3 pr-4 text-xs text-gray-500">{formatDate(template.created_at)}</td>
      <td className="py-3 pr-4 text-right space-x-1">
        <button
          onClick={() => onEdit(template)}
          className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          Edit
        </button>
        <button
          onClick={() => remove.mutate(template.id)}
          disabled={remove.isPending}
          className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
        >
          Delete
        </button>
      </td>
    </tr>
  )
}

export function NotificationTemplatesPage() {
  const { data: templates, isLoading, isError } = useNotificationTemplates()
  const [editing, setEditing] = useState<NotificationTemplateRead | null>(null)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Notification Templates</h1>
        <p className="mt-1 text-sm text-gray-500">
          Customise the title and body sent for each severity level.
        </p>
      </div>

      <TemplateForm editing={editing} onDone={() => setEditing(null)} />

      {isLoading && <p className="text-sm text-gray-500">Loading templates…</p>}
      {isError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Could not load notification templates. Make sure the API is running.
        </div>
      )}
      {!isLoading && !isError && templates && templates.length === 0 && (
        <p className="text-sm text-gray-500">No templates configured. Using built-in defaults.</p>
      )}
      {!isLoading && !isError && templates && templates.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="py-3 pr-4 pl-4">Name</th>
                <th className="py-3 pr-4">Severity</th>
                <th className="py-3 pr-4">Title template</th>
                <th className="py-3 pr-4">Default</th>
                <th className="py-3 pr-4">Created</th>
                <th className="py-3 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {templates.map((t) => (
                <TemplateRow key={t.id} template={t} onEdit={setEditing} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
